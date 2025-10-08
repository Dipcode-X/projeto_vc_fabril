from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import sqlite3
from central_manager.database.connection import DatabaseManager

router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"],
)

@router.get("", summary="Lista todos os produtos configurados")
async def get_produtos():
    """
    Retorna uma lista de produtos a partir do banco de dados.
    Inclui campos básicos e o config_json do produto.
    """
    db = DatabaseManager()
    produtos = db.get_produtos(ativo_only=True)
    # Converte os modelos Pydantic para dicts serializáveis
    return [p.model_dump() for p in produtos]

class ProdutoUpdatePartial(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    itens_por_camada: Optional[int] = None
    max_camadas: Optional[int] = None
    requires_divisor: Optional[bool] = None
    item_model: Optional[str] = None
    roi_model: Optional[str] = None
    conf_roi: Optional[float] = None
    conf_item: Optional[float] = None
    conf_divisor: Optional[float] = None

@router.put("/{produto_id}", summary="Atualiza parcialmente um produto")
async def update_produto(produto_id: int, body: ProdutoUpdatePartial):
    db = DatabaseManager()
    produto = db.get_produto(produto_id)
    if not produto:
        return {"error": f"Produto {produto_id} não encontrado"}

    cfg = produto.config_json or {}
    changed_cfg = False

    if body.requires_divisor is not None:
        cfg['requires_divisor'] = bool(body.requires_divisor)
        changed_cfg = True
    if body.item_model is not None:
        cfg['item_model'] = body.item_model
        changed_cfg = True
    if body.roi_model is not None:
        cfg['roi_model'] = body.roi_model
        changed_cfg = True
    if body.conf_roi is not None:
        cfg['conf_roi'] = float(body.conf_roi)
        changed_cfg = True
    if body.conf_item is not None:
        cfg['conf_item'] = float(body.conf_item)
        changed_cfg = True
    if body.conf_divisor is not None:
        cfg['conf_divisor'] = float(body.conf_divisor)
        changed_cfg = True

    set_parts = []
    params = []
    if body.nome is not None:
        set_parts.append("nome = ?")
        params.append(body.nome)
    if body.descricao is not None:
        set_parts.append("descricao = ?")
        params.append(body.descricao)
    if body.itens_por_camada is not None:
        set_parts.append("itens_por_camada = ?")
        params.append(int(body.itens_por_camada))
    if body.max_camadas is not None:
        set_parts.append("max_camadas = ?")
        params.append(int(body.max_camadas))
    if changed_cfg:
        set_parts.append("config_json = ?")
        params.append(json.dumps(cfg))

    if not set_parts:
        # Nada para atualizar
        return produto.model_dump()

    with db.get_connection() as conn:
        cur = conn.cursor()
        query = f"UPDATE produtos SET {', '.join(set_parts)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        params.append(produto_id)
        cur.execute(query, params)
        conn.commit()

    # Retorna produto atualizado
    updated = db.get_produto(produto_id)
    return updated.model_dump()

# --- Criação de produto ---
class ProdutoCreateAPI(BaseModel):
    nome: str
    descricao: Optional[str] = None
    itens_por_camada: int = 12
    max_camadas: int = 2
    requires_divisor: bool = True
    item_model: Optional[str] = None
    roi_model: Optional[str] = None

@router.post("", summary="Cria um novo produto")
async def create_produto(body: ProdutoCreateAPI):
    db = DatabaseManager()
    cfg = {}
    if body.item_model is not None:
        cfg['item_model'] = body.item_model
    if body.roi_model is not None:
        cfg['roi_model'] = body.roi_model
    cfg['requires_divisor'] = bool(body.requires_divisor)

    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO produtos (nome, descricao, itens_por_camada, max_camadas, config_json, ativo)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (body.nome, body.descricao, int(body.itens_por_camada), int(body.max_camadas), json.dumps(cfg))
        )
        conn.commit()
        new_id = cur.lastrowid

    new_prod = db.get_produto(new_id)
    return new_prod.model_dump()

# --- Exclusão de produto ---
@router.delete("/{produto_id}", summary="Remove um produto")
async def delete_produto(produto_id: int):
    db = DatabaseManager()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
        conn.commit()
    return {"deleted": True, "id": produto_id}

# --- Alterar ID (rekey) de produto com atualização em cascata nas câmeras ---
class ProdutoRekey(BaseModel):
    new_id: int

@router.put("/{produto_id}/rekey", summary="Altera o ID do produto e atualiza referências em câmeras")
async def rekey_produto(produto_id: int, body: ProdutoRekey):
    db = DatabaseManager()
    old_id = int(produto_id)
    new_id = int(body.new_id)
    if new_id == old_id:
        raise HTTPException(status_code=400, detail="new_id igual ao id atual")

    with db.get_connection() as conn:
        cur = conn.cursor()
        # Verifica existência do produto antigo
        cur.execute("SELECT * FROM produtos WHERE id = ?", (old_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Produto {old_id} não encontrado")
        # Garante que o novo ID não exista
        cur.execute("SELECT 1 FROM produtos WHERE id = ?", (new_id,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"Produto {new_id} já existe")

        # Duplica a linha com o novo ID (usa nome temporário para evitar violação de UNIQUE(nome))
        d = dict(row)
        original_nome = d.get("nome")
        tmp_nome = f"{original_nome}__tmp_{old_id}_{new_id}"

        insert_sql = (
            """
            INSERT INTO produtos (
                id, nome, descricao, itens_por_camada, max_camadas,
                confidence_threshold, divisor_confidence, divisor_low_confidence,
                buffer_size_roi, buffer_size_divisor, frames_estabilizacao,
                distancia_minima_item, percentual_itens_novos_minimo,
                carencia_caixa_ausente, carencia_divisor_ausente, timeout_alerta_minimo,
                tolerancia_oclusao_camada2, limiar_salto_contagem, tempo_validacao_salto,
                config_json, ativo, created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            insert_sql,
            (
                new_id,
                tmp_nome, d.get("descricao"), d.get("itens_por_camada"), d.get("max_camadas"),
                d.get("confidence_threshold"), d.get("divisor_confidence"), d.get("divisor_low_confidence"),
                d.get("buffer_size_roi"), d.get("buffer_size_divisor"), d.get("frames_estabilizacao"),
                d.get("distancia_minima_item"), d.get("percentual_itens_novos_minimo"),
                d.get("carencia_caixa_ausente"), d.get("carencia_divisor_ausente"), d.get("timeout_alerta_minimo"),
                d.get("tolerancia_oclusao_camada2"), d.get("limiar_salto_contagem"), d.get("tempo_validacao_salto"),
                d.get("config_json"), d.get("ativo"), d.get("created_at"),
            )
        )

        # Reaponta câmeras para o novo ID
        cur.execute(
            "UPDATE cameras SET produto_id = ?, updated_at = CURRENT_TIMESTAMP WHERE produto_id = ?",
            (new_id, old_id),
        )
        cameras_updated = cur.rowcount

        # Remove produto antigo
        cur.execute("DELETE FROM produtos WHERE id = ?", (old_id,))
        # Restaura o nome original no novo registro
        cur.execute(
            "UPDATE produtos SET nome = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (original_nome, new_id),
        )
        conn.commit()

    # Retorna novo produto e resumo
    updated = db.get_produto(new_id)
    return {
        "old_id": old_id,
        "new_id": new_id,
        "cameras_updated": cameras_updated,
        "produto": updated.model_dump() if updated else None,
    }
