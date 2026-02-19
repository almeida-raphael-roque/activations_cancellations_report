import duckdb
import boto3
import pandas as pd
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÕES E CREDENCIAIS ---
BUCKET = "transdesk-develop-bronze"
DATA_INICIO = "2025-08-01"
DATA_FIM = "2026-01-05"

# Mapeamento de Schemas (Esquerda=SQL, Direita=Pasta S3)
SCHEMAS = {
    'silver': 'vilesoft',
    'stcoop': 'stcoop',
    'viavante': 'viavante',
    'tag': 'tag'
}

# Lista de tabelas necessárias (Atualizada com as tabelas dos SQLs de Cancelamento)
TABELAS = [
    "insurance_registration", "insurance_reg_set", "cliente", "catalogo", 
    "representante", "insurance_status", "insurance_reg_set_coverage", 
    "insurance_vehicle", "tipo_veiculo", "insurance_reg_set_cov_trailer", 
    "insurance_trailer", "vendedor", "price_list_benefits", "type_category", 
    "category", "benefits", "web_user", "insurance_reg_historic"
]

# --- 2. INICIALIZAÇÃO DO DUCKDB ---
region = "sa-east-1"

con = duckdb.connect(database=':memory:')
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")

session = boto3.Session(region_name=region)
creds = session.get_credentials()
if not creds:
    raise Exception("Não foi possível encontrar credenciais AWS.")
creds = creds.get_frozen_credentials()

sets = [
    f"SET s3_region='{region}';",
    f"SET s3_access_key_id='{creds.access_key}';",
    f"SET s3_secret_access_key='{creds.secret_key}';",
]
if getattr(creds, "token", None):
    sets.append(f"SET s3_session_token='{creds.token}';")
con.execute("\n".join(sets))
con.execute("SET s3_endpoint='s3.sa-east-1.amazonaws.com';")

s3 = session.client("s3")

def listar_parquets_s3(bucket_name: str, prefix_path: str) -> list[str]:
    urls = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix_path):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".parquet"):
                urls.append(f"s3://{bucket_name}/{key}")
    return urls

def uma_url_parquet_qualquer(bucket_name: str, s3_folder: str, tb: str):
    prefix = f"{s3_folder}/{tb.lower()}/"
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix, PaginationConfig={"MaxItems": 10}):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".parquet"):
                return f"s3://{bucket_name}/{key}"
    return None

# Cria schemas no DuckDB
for sql_schema_name in SCHEMAS.keys():
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {sql_schema_name};")

# --- 3. QUERIES SQL (ADAPTADAS PARA DUCKDB) ---

# Query 1: Cancelamentos Integrais
# Nota: Ajustei 'date_add' para sintaxe padrão ANSI/DuckDB (data - INTERVAL 'X' DAY)
QUERY_INTEGRAIS = """
WITH CTE_segtruck AS (
    SELECT
        coalesce(iv.BOARD,it.BOARD,itt.BOARD) as placa,
        coalesce(iv.chassi,it.chassi,itt.chassi) as chassi,
        coalesce(iv.id,it.id,itt.id) as id_placa,
        coalesce(irsc.ID_VEHICLE) as id_veiculo,
        coalesce(irsct.ID_TRAILER) as id_carroceria,
        ir.id as matricula,
        irs.id as conjunto,
        cata.fantasia as unidade,
        v.DESCRICAO as consultor,
        iss.description as status,
        cat.nome as cliente,
        user_name.suporte as usuario_suporte,
        irs.user_name_cancellation as usuario_cancelamento,
        irsc.id as coverage_id,
        b.description as beneficio,
        isss.description as status_beneficio,
        current_date AS data_extracao,
        irs.data_registration as data_registro,
        cast(coalesce(irs.DATE_INITAL_EFFECT, irs.DATE_FINAL_EFFECT - INTERVAL '364' DAY) as date) as data_ativacao,
        cast(coalesce(irsc.date_initial_effect, irsc.date_final_effect - INTERVAL '364' DAY) as date) as data_ativacao_beneficio,
        cast(irs.date_cancellation as date) as data_cancelamento,
        ROW_NUMBER() OVER (PARTITION BY coalesce(iv.chassi,it.chassi,itt.chassi) ORDER BY irs.data_registration DESC) as rn,
        'Segtruck' as empresa
    FROM silver.insurance_registration ir
        LEFT JOIN silver.insurance_reg_set irs ON irs.parent = ir.id
        LEFT JOIN silver.cliente clie ON clie.codigo = ir.CUSTOMER_ID
        LEFT JOIN silver.catalogo cat ON cat.cnpj_cpf = clie.cnpj_cpf
        LEFT JOIN silver.representante r ON r.codigo = irs.id_unity
        LEFT JOIN silver.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
        LEFT JOIN silver.insurance_status iss ON iss.id = irs.id_status
        LEFT JOIN silver.INSURANCE_REG_SET_COVERAGE irsc ON irsc.PARENT = irs.ID
        LEFT JOIN silver.INSURANCE_VEHICLE iv ON iv.ID = irsc.ID_VEHICLE
        LEFT JOIN silver.TIPO_VEICULO tv ON tv.CODIGO = iv.CODE_TYPE_VEHICLE 
        LEFT JOIN silver.INSURANCE_REG_SET_COV_TRAILER irsct ON irsct.PARENT = irsc.ID
        LEFT JOIN silver.INSURANCE_TRAILER it ON it.ID = irsct.ID_TRAILER
        LEFT JOIN silver.insurance_trailer itt ON itt.id = irsc.ID_TRAILER
        LEFT JOIN silver.insurance_reg_historic irh ON irh.id_set = irs.id
        LEFT JOIN silver.VENDEDOR v ON v.CODIGO = irs.ID_CONSULTANT
        LEFT JOIN silver.price_list_benefits plb on plb.id = irsc.id_price_list
        LEFT JOIN silver.type_category tc on tc.id = plb.id_type_category
        LEFT JOIN silver.category c on c.id = tc.id_category
        LEFT JOIN silver.benefits b on b.id = c.id_benefits
        LEFT JOIN silver.insurance_status isss on isss.id = irsc.id_status
        LEFT JOIN (
            SELECT DISTINCT irs.id as conjunto, wb.user_name as suporte
            FROM silver.insurance_reg_set irs 
            INNER JOIN silver.web_user wb ON wb.id = irs.id_user_support
        ) as user_name ON user_name.conjunto = irs.id
    WHERE date_cancellation IS NOT NULL
      AND coalesce(iv.BOARD,it.BOARD,itt.BOARD) IS NOT NULL
      AND coalesce(iv.chassi,it.chassi,itt.chassi) IS NOT NULL
),
CTE_stcoop AS (
    SELECT
        coalesce(iv.BOARD,it.BOARD,itt.BOARD) as placa,
        coalesce(iv.chassi,it.chassi,itt.chassi) as chassi,
        coalesce(iv.id,it.id,itt.id) as id_placa,
        coalesce(irsc.ID_VEHICLE) as id_veiculo,
        coalesce(irsct.ID_TRAILER) as id_carroceria,
        ir.id as matricula,
        irs.id as conjunto,
        cata.fantasia as unidade,
        v.DESCRICAO as consultor,
        iss.description as status,
        cat.nome as cliente,
        user_name.suporte as usuario_suporte,
        irs.user_name_cancellation as usuario_cancelamento,
        irsc.id as coverage_id,
        b.description as beneficio,
        isss.description as status_beneficio,
        current_date AS data_extracao,
        irs.data_registration as data_registro,
        cast(coalesce(irs.DATE_INITAL_EFFECT, irs.DATE_FINAL_EFFECT - INTERVAL '364' DAY) as date) as data_ativacao,
        cast(coalesce(irsc.date_initial_effect, irsc.date_final_effect - INTERVAL '364' DAY) as date) as data_ativacao_beneficio,
        cast(irs.date_cancellation as date) as data_cancelamento,
        ROW_NUMBER() OVER (PARTITION BY coalesce(iv.chassi,it.chassi,itt.chassi) ORDER BY irs.data_registration DESC) as rn,
        'Stcoop' as empresa
    FROM stcoop.insurance_registration ir
        LEFT JOIN stcoop.insurance_reg_set irs ON irs.parent = ir.id
        LEFT JOIN stcoop.cliente clie ON clie.codigo = ir.CUSTOMER_ID
        LEFT JOIN stcoop.catalogo cat ON cat.cnpj_cpf = clie.cnpj_cpf
        LEFT JOIN stcoop.representante r ON r.codigo = irs.id_unity
        LEFT JOIN stcoop.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
        LEFT JOIN stcoop.insurance_status iss ON iss.id = irs.id_status
        LEFT JOIN stcoop.INSURANCE_REG_SET_COVERAGE irsc ON irsc.PARENT = irs.ID
        LEFT JOIN stcoop.INSURANCE_VEHICLE iv ON iv.ID = irsc.ID_VEHICLE
        LEFT JOIN stcoop.TIPO_VEICULO tv ON tv.CODIGO = iv.CODE_TYPE_VEHICLE 
        LEFT JOIN stcoop.INSURANCE_REG_SET_COV_TRAILER irsct ON irsct.PARENT = irsc.ID
        LEFT JOIN stcoop.INSURANCE_TRAILER it ON it.ID = irsct.ID_TRAILER
        LEFT JOIN stcoop.insurance_trailer itt ON itt.id = irsc.ID_TRAILER
        LEFT JOIN stcoop.insurance_reg_historic irh ON irh.id_set = irs.id
        LEFT JOIN stcoop.VENDEDOR v ON v.CODIGO = irs.ID_CONSULTANT
        LEFT JOIN stcoop.price_list_benefits plb on plb.id = irsc.id_price_list
        LEFT JOIN stcoop.type_category tc on tc.id = plb.id_type_category
        LEFT JOIN stcoop.category c on c.id = tc.id_category
        LEFT JOIN stcoop.benefits b on b.id = c.id_benefits
        LEFT JOIN stcoop.insurance_status isss on isss.id = irsc.id_status
        LEFT JOIN (
            SELECT DISTINCT irs.id as conjunto, wb.user_name as suporte
            FROM stcoop.insurance_reg_set irs 
            INNER JOIN stcoop.web_user wb ON wb.id = irs.id_user_support
        ) as user_name ON user_name.conjunto = irs.id
    WHERE date_cancellation IS NOT NULL
      AND coalesce(iv.BOARD,it.BOARD,itt.BOARD) IS NOT NULL
      AND coalesce(iv.chassi,it.chassi,itt.chassi) IS NOT NULL
),
CTE_viavante AS (
    SELECT
        coalesce(iv.BOARD,it.BOARD,itt.BOARD) as placa,
        coalesce(iv.chassi,it.chassi,itt.chassi) as chassi,
        coalesce(iv.id,it.id,itt.id) as id_placa,
        coalesce(irsc.ID_VEHICLE) as id_veiculo,
        coalesce(irsct.ID_TRAILER) as id_carroceria,
        ir.id as matricula,
        irs.id as conjunto,
        cata.fantasia as unidade,
        v.DESCRICAO as consultor,
        iss.description as status,
        cat.nome as cliente,
        user_name.suporte as usuario_suporte,
        irs.user_name_cancellation as usuario_cancelamento,
        irsc.id as coverage_id,
        b.description as beneficio,
        isss.description as status_beneficio,
        current_date AS data_extracao,
        irs.data_registration as data_registro,
        cast(coalesce(irs.DATE_INITAL_EFFECT, irs.DATE_FINAL_EFFECT - INTERVAL '364' DAY) as date) as data_ativacao,
        cast(coalesce(irsc.date_initial_effect, irsc.date_final_effect - INTERVAL '364' DAY) as date) as data_ativacao_beneficio,
        cast(irs.date_cancellation as date) as data_cancelamento,
        ROW_NUMBER() OVER (PARTITION BY coalesce(iv.chassi,it.chassi,itt.chassi) ORDER BY irs.data_registration DESC) as rn,
        'Viavante' as empresa
    FROM viavante.insurance_registration ir
        LEFT JOIN viavante.insurance_reg_set irs ON irs.parent = ir.id
        LEFT JOIN viavante.cliente clie ON clie.codigo = ir.CUSTOMER_ID
        LEFT JOIN viavante.catalogo cat ON cat.cnpj_cpf = clie.cnpj_cpf
        LEFT JOIN viavante.representante r ON r.codigo = irs.id_unity
        LEFT JOIN viavante.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
        LEFT JOIN viavante.insurance_status iss ON iss.id = irs.id_status
        LEFT JOIN viavante.INSURANCE_REG_SET_COVERAGE irsc ON irsc.PARENT = irs.ID
        LEFT JOIN viavante.INSURANCE_VEHICLE iv ON iv.ID = irsc.ID_VEHICLE
        LEFT JOIN viavante.TIPO_VEICULO tv ON tv.CODIGO = iv.CODE_TYPE_VEHICLE 
        LEFT JOIN viavante.INSURANCE_REG_SET_COV_TRAILER irsct ON irsct.PARENT = irsc.ID
        LEFT JOIN viavante.INSURANCE_TRAILER it ON it.ID = irsct.ID_TRAILER
        LEFT JOIN viavante.insurance_trailer itt ON itt.id = irsc.ID_TRAILER
        LEFT JOIN viavante.insurance_reg_historic irh ON irh.id_set = irs.id
        LEFT JOIN viavante.VENDEDOR v ON v.CODIGO = irs.ID_CONSULTANT
        LEFT JOIN viavante.price_list_benefits plb on plb.id = irsc.id_price_list
        LEFT JOIN viavante.type_category tc on tc.id = plb.id_type_category
        LEFT JOIN viavante.category c on c.id = tc.id_category
        LEFT JOIN viavante.benefits b on b.id = c.id_benefits
        LEFT JOIN viavante.insurance_status isss on isss.id = irsc.id_status
        LEFT JOIN (
            SELECT DISTINCT irs.id as conjunto, wb.user_name as suporte
            FROM viavante.insurance_reg_set irs 
            INNER JOIN viavante.web_user wb ON wb.id = irs.id_user_support
        ) as user_name ON user_name.conjunto = irs.id
    WHERE date_cancellation IS NOT NULL
      AND coalesce(iv.BOARD,it.BOARD,itt.BOARD) IS NOT NULL
      AND coalesce(iv.chassi,it.chassi,itt.chassi) IS NOT NULL
),
CTE_tag AS (
    SELECT
        coalesce(iv.BOARD,it.BOARD,itt.BOARD) as placa,
        coalesce(iv.chassi,it.chassi,itt.chassi) as chassi,
        coalesce(iv.id,it.id,itt.id) as id_placa,
        coalesce(irsc.ID_VEHICLE) as id_veiculo,
        coalesce(irsct.ID_TRAILER) as id_carroceria,
        ir.id as matricula,
        irs.id as conjunto,
        cata.fantasia as unidade,
        v.DESCRICAO as consultor,
        iss.description as status,
        cat.nome as cliente,
        user_name.suporte as usuario_suporte,
        irs.user_name_cancellation as usuario_cancelamento,
        irsc.id as coverage_id,
        b.description as beneficio,
        isss.description as status_beneficio,
        current_date AS data_extracao,
        irs.data_registration as data_registro,
        cast(coalesce(irs.DATE_INITAL_EFFECT, irs.DATE_FINAL_EFFECT - INTERVAL '364' DAY) as date) as data_ativacao,
        cast(coalesce(irsc.date_initial_effect, irsc.date_final_effect - INTERVAL '364' DAY) as date) as data_ativacao_beneficio,
        cast(irs.date_cancellation as date) as data_cancelamento,
        ROW_NUMBER() OVER (PARTITION BY coalesce(iv.chassi,it.chassi,itt.chassi) ORDER BY irs.data_registration DESC) as rn,
        'Tag' as empresa
    FROM tag.insurance_registration ir
        LEFT JOIN tag.insurance_reg_set irs ON irs.parent = ir.id
        LEFT JOIN tag.cliente clie ON clie.codigo = ir.CUSTOMER_ID
        LEFT JOIN tag.catalogo cat ON cat.cnpj_cpf = clie.cnpj_cpf
        LEFT JOIN tag.representante r ON r.codigo = irs.id_unity
        LEFT JOIN tag.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
        LEFT JOIN tag.insurance_status iss ON iss.id = irs.id_status
        LEFT JOIN tag.INSURANCE_REG_SET_COVERAGE irsc ON irsc.PARENT = irs.ID
        LEFT JOIN tag.INSURANCE_VEHICLE iv ON iv.ID = irsc.ID_VEHICLE
        LEFT JOIN tag.TIPO_VEICULO tv ON tv.CODIGO = iv.CODE_TYPE_VEHICLE 
        LEFT JOIN tag.INSURANCE_REG_SET_COV_TRAILER irsct ON irsct.PARENT = irsc.ID
        LEFT JOIN tag.INSURANCE_TRAILER it ON it.ID = irsct.ID_TRAILER
        LEFT JOIN tag.insurance_trailer itt ON itt.id = irsc.ID_TRAILER
        LEFT JOIN tag.insurance_reg_historic irh ON irh.id_set = irs.id
        LEFT JOIN tag.VENDEDOR v ON v.CODIGO = irs.ID_CONSULTANT
        LEFT JOIN tag.price_list_benefits plb on plb.id = irsc.id_price_list
        LEFT JOIN tag.type_category tc on tc.id = plb.id_type_category
        LEFT JOIN tag.category c on c.id = tc.id_category
        LEFT JOIN tag.benefits b on b.id = c.id_benefits
        LEFT JOIN tag.insurance_status isss on isss.id = irsc.id_status
        LEFT JOIN (
            SELECT DISTINCT irs.id as conjunto, wb.user_name as suporte
            FROM tag.insurance_reg_set irs 
            INNER JOIN tag.web_user wb ON wb.id = irs.id_user_support
        ) as user_name ON user_name.conjunto = irs.id
    WHERE date_cancellation IS NOT NULL
      AND coalesce(iv.BOARD,it.BOARD,itt.BOARD) IS NOT NULL
      AND coalesce(iv.chassi,it.chassi,itt.chassi) IS NOT NULL
)
SELECT * FROM (
    SELECT * FROM CTE_segtruck WHERE rn = 1
    UNION ALL
    SELECT * FROM CTE_stcoop WHERE rn = 1
    UNION ALL
    SELECT * FROM CTE_viavante WHERE rn = 1
    UNION ALL
    SELECT * FROM CTE_tag WHERE rn = 1
) AS final
WHERE data_cancelamento >= DATE '2025-01-01'
"""

# Query 2: Cancelamentos Parciais
QUERY_PARCIAIS = """
SELECT DISTINCT
    coalesce(iv.BOARD,it.BOARD,itt.BOARD) as placa,
    coalesce(iv.chassi,it.chassi,itt.chassi) as chassi,
    coalesce(iv.id,it.id,itt.id) as id_placa,
    coalesce(irsc.ID_VEHICLE) as id_veiculo,
    coalesce(irsct.ID_TRAILER) as id_carroceria,
    ir.id as matricula,
    irs.id as conjunto,
    cata.fantasia as unidade,
    v.DESCRICAO as consultor,
    iss.description as status,
    cat.nome as cliente,
    user_name.suporte as usuario_suporte,
    irs.user_name_cancellation as usuario_cancelamento,
    irsc.id as coverage_id,
    b.description as beneficio,
    isss.description as status_beneficio,
    current_date AS data_extracao,
    irs.data_registration as data_registro,
    cast(coalesce(irs.DATE_INITAL_EFFECT, irs.DATE_FINAL_EFFECT - INTERVAL '364' DAY) as date) as data_ativacao,
    cast(coalesce(irsc.date_initial_effect, irsc.date_final_effect - INTERVAL '364' DAY) as date) as data_ativacao_beneficio,
    -- Conversão de timestamp ticks C# para Data
    CAST('1900-01-01 00:00:00' AS TIMESTAMP) 
    + (irsc.UPDATED_AT - 599266080000000000) / 864000000000 * INTERVAL '1' DAY AS data_atualizacao,
    'Segtruck' as empresa
FROM silver.insurance_registration ir
    LEFT OUTER JOIN silver.insurance_reg_set irs on irs.parent = ir.id
    LEFT OUTER JOIN silver.cliente clie on clie.codigo = ir.CUSTOMER_ID
    LEFT OUTER JOIN silver.catalogo cat on cat.cnpj_cpf = clie.cnpj_cpf
    LEFT OUTER JOIN silver.representante r on r.codigo = irs.id_unity
    LEFT OUTER JOIN silver.catalogo cata on cata.cnpj_cpf = r.cnpj_cpf
    LEFT OUTER JOIN silver.insurance_status iss on iss.id = irs.id_status
    LEFT OUTER JOIN silver.INSURANCE_REG_SET_COVERAGE irsc ON irsc.PARENT = irs.ID
    LEFT OUTER JOIN silver.INSURANCE_VEHICLE iv on iv.ID = irsc.ID_VEHICLE
    LEFT OUTER JOIN silver.TIPO_VEICULO tv on tv.CODIGO = iv.CODE_TYPE_VEHICLE 
    LEFT OUTER JOIN silver.INSURANCE_REG_SET_COV_TRAILER irsct on irsct.PARENT = irsc.ID
    LEFT OUTER JOIN silver.INSURANCE_TRAILER it on it.ID = irsct.ID_TRAILER
    LEFT OUTER JOIN silver.insurance_trailer itt on itt.id = irsc.ID_TRAILER
    LEFT OUTER JOIN silver.vendedor v on v.CODIGO = irs.ID_CONSULTANT
    LEFT OUTER JOIN silver.insurance_status isss on isss.id = irsc.id_status
    LEFT OUTER JOIN silver.price_list_benefits plb on plb.id = irsc.id_price_list
    LEFT OUTER JOIN silver.type_category tc on tc.id = plb.id_type_category
    LEFT OUTER JOIN silver.category c on c.id = tc.id_category
    LEFT OUTER JOIN silver.benefits b on b.id = c.id_benefits
    LEFT OUTER JOIN (
        select distinct irs.id as conjunto, wb.user_name as suporte
        from silver.insurance_reg_set irs 
        inner join silver.web_user wb on wb.id = irs.id_user_support
    ) as user_name on user_name.conjunto = irs.id
WHERE iss.id = 7
  AND (coalesce(iv.BOARD,it.BOARD,itt.BOARD) is not null AND coalesce(iv.chassi,it.chassi,itt.chassi) is not null)
  AND isss.description <> 'ATIVO'
  AND CAST('1900-01-01 00:00:00' AS TIMESTAMP) 
      + (irsc.UPDATED_AT - 599266080000000000) / 864000000000 * INTERVAL '1' DAY >= TIMESTAMP '2025-01-01 00:00:00'

UNION ALL

SELECT DISTINCT
    coalesce(iv.BOARD,it.BOARD,itt.BOARD) as placa,
    coalesce(iv.chassi,it.chassi,itt.chassi) as chassi,
    coalesce(iv.id,it.id,itt.id) as id_placa,
    coalesce(irsc.ID_VEHICLE) as id_veiculo,
    coalesce(irsct.ID_TRAILER) as id_carroceria,
    ir.id as matricula,
    irs.id as conjunto,
    cata.fantasia as unidade,
    v.DESCRICAO as consultor,
    iss.description as status,
    cat.nome as cliente,
    user_name.suporte as usuario_suporte,
    irs.user_name_cancellation as usuario_cancelamento,
    irsc.id as coverage_id,
    b.description as beneficio,
    isss.description as status_beneficio,
    current_date AS data_extracao,
    irs.data_registration as data_registro,
    cast(coalesce(irs.DATE_INITAL_EFFECT, irs.DATE_FINAL_EFFECT - INTERVAL '364' DAY) as date) as data_ativacao,
    cast(coalesce(irsc.date_initial_effect, irsc.date_final_effect - INTERVAL '364' DAY) as date) as data_ativacao_beneficio,
    CAST('1900-01-01 00:00:00' AS TIMESTAMP) 
    + (irsc.UPDATED_AT - 599266080000000000) / 864000000000 * INTERVAL '1' DAY AS data_atualizacao,
    'Stcoop' as empresa
FROM stcoop.insurance_registration ir
    LEFT OUTER JOIN stcoop.insurance_reg_set irs on irs.parent = ir.id
    LEFT OUTER JOIN stcoop.cliente clie on clie.codigo = ir.CUSTOMER_ID
    LEFT OUTER JOIN stcoop.catalogo cat on cat.cnpj_cpf = clie.cnpj_cpf
    LEFT OUTER JOIN stcoop.representante r on r.codigo = irs.id_unity
    LEFT OUTER JOIN stcoop.catalogo cata on cata.cnpj_cpf = r.cnpj_cpf
    LEFT OUTER JOIN stcoop.insurance_status iss on iss.id = irs.id_status
    LEFT OUTER JOIN stcoop.INSURANCE_REG_SET_COVERAGE irsc ON irsc.PARENT = irs.ID
    LEFT OUTER JOIN stcoop.INSURANCE_VEHICLE iv on iv.ID = irsc.ID_VEHICLE
    LEFT OUTER JOIN stcoop.TIPO_VEICULO tv ON tv.CODIGO = iv.CODE_TYPE_VEHICLE 
    LEFT OUTER JOIN stcoop.INSURANCE_REG_SET_COV_TRAILER irsct on irsct.PARENT = irsc.ID
    LEFT OUTER JOIN stcoop.INSURANCE_TRAILER it on it.ID = irsct.ID_TRAILER
    LEFT OUTER JOIN stcoop.insurance_trailer itt on itt.id = irsc.ID_TRAILER
    LEFT OUTER JOIN stcoop.vendedor v on v.CODIGO = irs.ID_CONSULTANT
    LEFT OUTER JOIN stcoop.insurance_status isss on isss.id = irsc.id_status
    LEFT OUTER JOIN stcoop.price_list_benefits plb on plb.id = irsc.id_price_list
    LEFT OUTER JOIN stcoop.type_category tc on tc.id = plb.id_type_category
    LEFT OUTER JOIN stcoop.category c on c.id = tc.id_category
    LEFT OUTER JOIN stcoop.benefits b on b.id = c.id_benefits
    LEFT OUTER JOIN (
        select distinct irs.id as conjunto, wb.user_name as suporte
        from stcoop.insurance_reg_set irs 
        inner join stcoop.web_user wb on wb.id = irs.id_user_support
    ) as user_name on user_name.conjunto = irs.id
WHERE iss.id = 7
  AND (coalesce(iv.BOARD,it.BOARD,itt.BOARD) is not null AND coalesce(iv.chassi,it.chassi,itt.chassi) is not null)
  AND isss.description <> 'ATIVO'
  AND CAST('1900-01-01 00:00:00' AS TIMESTAMP) 
      + (irsc.UPDATED_AT - 599266080000000000) / 864000000000 * INTERVAL '1' DAY >= TIMESTAMP '2025-01-01 00:00:00'

UNION ALL

SELECT DISTINCT
    coalesce(iv.BOARD,it.BOARD,itt.BOARD) as placa,
    coalesce(iv.chassi,it.chassi,itt.chassi) as chassi,
    coalesce(iv.id,it.id,itt.id) as id_placa,
    coalesce(irsc.ID_VEHICLE) as id_veiculo,
    coalesce(irsct.ID_TRAILER) as id_carroceria,
    ir.id as matricula,
    irs.id as conjunto,
    cata.fantasia as unidade,
    v.DESCRICAO as consultor,
    iss.description as status,
    cat.nome as cliente,
    user_name.suporte as usuario_suporte,
    irs.user_name_cancellation as usuario_cancelamento,
    irsc.id as coverage_id,
    b.description as beneficio,
    isss.description as status_beneficio,
    current_date AS data_extracao,
    irs.data_registration as data_registro,
    cast(coalesce(irs.DATE_INITAL_EFFECT, irs.DATE_FINAL_EFFECT - INTERVAL '364' DAY) as date) as data_ativacao,
    cast(coalesce(irsc.date_initial_effect, irsc.date_final_effect - INTERVAL '364' DAY) as date) as data_ativacao_beneficio,
    CAST('1900-01-01 00:00:00' AS TIMESTAMP) 
    + (irsc.UPDATED_AT - 599266080000000000) / 864000000000 * INTERVAL '1' DAY AS data_atualizacao,
    'Viavante' as empresa
FROM viavante.insurance_registration ir
    LEFT OUTER JOIN viavante.insurance_reg_set irs on irs.parent = ir.id
    LEFT OUTER JOIN viavante.cliente clie on clie.codigo = ir.CUSTOMER_ID
    LEFT OUTER JOIN viavante.catalogo cat on cat.cnpj_cpf = clie.cnpj_cpf
    LEFT OUTER JOIN viavante.representante r on r.codigo = irs.id_unity
    LEFT OUTER JOIN viavante.catalogo cata on cata.cnpj_cpf = r.cnpj_cpf
    LEFT OUTER JOIN viavante.insurance_status iss on iss.id = irs.id_status
    LEFT OUTER JOIN viavante.INSURANCE_REG_SET_COVERAGE irsc ON irsc.PARENT = irs.ID
    LEFT OUTER JOIN viavante.INSURANCE_VEHICLE iv on iv.ID = irsc.ID_VEHICLE
    LEFT OUTER JOIN viavante.TIPO_VEICULO tv ON tv.CODIGO = iv.CODE_TYPE_VEHICLE 
    LEFT OUTER JOIN viavante.INSURANCE_REG_SET_COV_TRAILER irsct on irsct.PARENT = irsc.ID
    LEFT OUTER JOIN viavante.INSURANCE_TRAILER it on it.ID = irsct.ID_TRAILER
    LEFT OUTER JOIN viavante.insurance_trailer itt on itt.id = irsc.ID_TRAILER
    LEFT OUTER JOIN viavante.vendedor v on v.CODIGO = irs.ID_CONSULTANT
    LEFT OUTER JOIN viavante.insurance_status isss on isss.id = irsc.id_status
    LEFT OUTER JOIN viavante.price_list_benefits plb on plb.id = irsc.id_price_list
    LEFT OUTER JOIN viavante.type_category tc on tc.id = plb.id_type_category
    LEFT OUTER JOIN viavante.category c on c.id = tc.id_category
    LEFT OUTER JOIN viavante.benefits b on b.id = c.id_benefits
    LEFT OUTER JOIN (
        select distinct irs.id as conjunto, wb.user_name as suporte
        from viavante.insurance_reg_set irs 
        inner join viavante.web_user wb on wb.id = irs.id_user_support
    ) as user_name on user_name.conjunto = irs.id
WHERE iss.id = 7
  AND (coalesce(iv.BOARD,it.BOARD,itt.BOARD) is not null AND coalesce(iv.chassi,it.chassi,itt.chassi) is not null)
  AND isss.description <> 'ATIVO'
  AND CAST('1900-01-01 00:00:00' AS TIMESTAMP) 
      + (irsc.UPDATED_AT - 599266080000000000) / 864000000000 * INTERVAL '1' DAY >= TIMESTAMP '2025-01-01 00:00:00'

UNION ALL

SELECT DISTINCT
    coalesce(iv.BOARD,it.BOARD,itt.BOARD) as placa,
    coalesce(iv.chassi,it.chassi,itt.chassi) as chassi,
    coalesce(iv.id,it.id,itt.id) as id_placa,
    coalesce(irsc.ID_VEHICLE) as id_veiculo,
    coalesce(irsct.ID_TRAILER) as id_carroceria,
    ir.id as matricula,
    irs.id as conjunto,
    cata.fantasia as unidade,
    v.DESCRICAO as consultor,
    iss.description as status,
    cat.nome as cliente,
    user_name.suporte as usuario_suporte,
    irs.user_name_cancellation as usuario_cancelamento,
    irsc.id as coverage_id,
    b.description as beneficio,
    isss.description as status_beneficio,
    current_date AS data_extracao,
    irs.data_registration as data_registro,
    cast(coalesce(irs.DATE_INITAL_EFFECT, irs.DATE_FINAL_EFFECT - INTERVAL '364' DAY) as date) as data_ativacao,
    cast(coalesce(irsc.date_initial_effect, irsc.date_final_effect - INTERVAL '364' DAY) as date) as data_ativacao_beneficio,
    CAST('1900-01-01 00:00:00' AS TIMESTAMP) 
    + (irsc.UPDATED_AT - 599266080000000000) / 864000000000 * INTERVAL '1' DAY AS data_atualizacao,
    'Tag' as empresa
FROM tag.insurance_registration ir
    LEFT OUTER JOIN tag.insurance_reg_set irs on irs.parent = ir.id
    LEFT OUTER JOIN tag.cliente clie on clie.codigo = ir.CUSTOMER_ID
    LEFT OUTER JOIN tag.catalogo cat on cat.cnpj_cpf = clie.cnpj_cpf
    LEFT OUTER JOIN tag.representante r on r.codigo = irs.id_unity
    LEFT OUTER JOIN tag.catalogo cata on cata.cnpj_cpf = r.cnpj_cpf
    LEFT OUTER JOIN tag.insurance_status iss on iss.id = irs.id_status
    LEFT OUTER JOIN tag.INSURANCE_REG_SET_COVERAGE irsc ON irsc.PARENT = irs.ID
    LEFT OUTER JOIN tag.INSURANCE_VEHICLE iv on iv.ID = irsc.ID_VEHICLE
    LEFT OUTER JOIN tag.TIPO_VEICULO tv ON tv.CODIGO = iv.CODE_TYPE_VEHICLE 
    LEFT OUTER JOIN tag.INSURANCE_REG_SET_COV_TRAILER irsct ON irsct.PARENT = irsc.ID
    LEFT OUTER JOIN tag.INSURANCE_TRAILER it on it.ID = irsct.ID_TRAILER
    LEFT OUTER JOIN tag.insurance_trailer itt ON itt.id = irsc.ID_TRAILER
    LEFT OUTER JOIN tag.vendedor v on v.CODIGO = irs.ID_CONSULTANT
    LEFT OUTER JOIN tag.insurance_status isss on isss.id = irsc.id_status
    LEFT OUTER JOIN tag.price_list_benefits plb on plb.id = irsc.id_price_list
    LEFT OUTER JOIN tag.type_category tc on tc.id = plb.id_type_category
    LEFT OUTER JOIN tag.category c on c.id = tc.id_category
    LEFT OUTER JOIN tag.benefits b on b.id = c.id_benefits
    LEFT OUTER JOIN (
        select distinct irs.id as conjunto, wb.user_name as suporte
        from tag.insurance_reg_set irs 
        inner join tag.web_user wb on wb.id = irs.id_user_support
    ) as user_name on user_name.conjunto = irs.id
WHERE iss.id = 7
  AND (coalesce(iv.BOARD,it.BOARD,itt.BOARD) is not null AND coalesce(iv.chassi,it.chassi,itt.chassi) is not null)
  AND isss.description <> 'ATIVO'
  AND CAST('1900-01-01 00:00:00' AS TIMESTAMP) 
      + (irsc.UPDATED_AT - 599266080000000000) / 864000000000 * INTERVAL '1' DAY >= TIMESTAMP '2025-01-01 00:00:00'
"""

# --- 4. LOOP DE EXECUÇÃO ---
resultados = []

def daterange(start_date, end_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    for n in range(int((end - start).days) + 1):
        yield (start + timedelta(n)).strftime("%Y-%m-%d")

print(f"Iniciando loop de {DATA_INICIO} a {DATA_FIM}...")

for dia_x in daterange(DATA_INICIO, DATA_FIM):
    print(f"-> Processando dia: {dia_x}")

    # A. MONTAR VIEWS (Ligar tabelas do S3 com DuckDB para este dia específico)
    criadas_com_dados = set()
    for sql_name, s3_folder in SCHEMAS.items():
        for tb in TABELAS:
            prefix = f"{s3_folder}/{tb.lower()}/landing_date={dia_x}/"
            urls = listar_parquets_s3(BUCKET, prefix)
            if urls:
                try:
                    paths_sql = ", ".join(repr(u) for u in urls)
                    con.execute(f"""
                        CREATE OR REPLACE VIEW {sql_name}.{tb} AS 
                        SELECT * FROM read_parquet([{paths_sql}])
                    """)
                    criadas_com_dados.add((sql_name, tb))
                except Exception as exc:
                    print(f"   Erro ao criar view {sql_name}.{tb} com dados: {exc}")

    # B. VIEWS VAZIAS (Fallback para tabelas que não existem neste dia)
    for sql_name, s3_folder in SCHEMAS.items():
        for tb in TABELAS:
            if (sql_name, tb) in criadas_com_dados:
                continue
            
            # Tenta copiar schema de outro cliente que tenha a tabela
            ref = None
            for outro in SCHEMAS.keys():
                if (outro, tb) in criadas_com_dados:
                    ref = outro
                    break
            
            if ref is not None:
                try:
                    con.execute(f"CREATE OR REPLACE VIEW {sql_name}.{tb} AS SELECT * FROM {ref}.{tb} WHERE 1=0")
                except:
                    pass
            else:
                # Se ninguém tem, pega um parquet aleatório do bucket para inferir schema
                uma_url = uma_url_parquet_qualquer(BUCKET, s3_folder, tb)
                if uma_url:
                    try:
                        con.execute(f"CREATE OR REPLACE VIEW {sql_name}.{tb} AS SELECT * FROM read_parquet([{repr(uma_url)}]) WHERE 1=0")
                    except:
                        pass

    # C. EXECUÇÃO DA LÓGICA DE CANCELAMENTOS
    try:
        # 1. Busca Cancelamentos Integrais
        df_cancelamentos_integrais = con.execute(QUERY_INTEGRAIS).df()
        
        # 2. Busca Cancelamentos Parciais
        df_cancelamentos_parciais = con.execute(QUERY_PARCIAIS).df()

        if df_cancelamentos_integrais.empty and df_cancelamentos_parciais.empty:
            count_cancelados = 0
            print("   Nenhum cancelamento encontrado neste snapshot.")
        else:
            # 3. Tratamento e Junção em Python (Conforme solicitado)
            
            # Adiciona Identificadores
            if not df_cancelamentos_integrais.empty:
                df_cancelamentos_integrais['identificador'] = 'INTEGRAL'
                # Garante formato de data
                df_cancelamentos_integrais['data_cancelamento'] = pd.to_datetime(
                    df_cancelamentos_integrais['data_cancelamento'], errors='coerce'
                )

            if not df_cancelamentos_parciais.empty:
                df_cancelamentos_parciais['identificador'] = 'PARCIAL'
                # Para parciais, 'data_cancelamento' não existe na query original, 
                # a lógica costuma usar 'data_atualizacao' como referência, 
                # mas para concatenar precisamos alinhar colunas.
                # Vou criar a coluna 'data_cancelamento' baseada na 'data_atualizacao' para permitir o sort.
                if 'data_atualizacao' in df_cancelamentos_parciais.columns:
                     df_cancelamentos_parciais['data_cancelamento'] = pd.to_datetime(
                        df_cancelamentos_parciais['data_atualizacao'], errors='coerce'
                     )
            
            # Concatenação
            df_cancelamentos = pd.concat(
                [df_cancelamentos_integrais, df_cancelamentos_parciais], ignore_index=True
            )

            # Ordenação por data (Decrescente)
            if 'data_cancelamento' in df_cancelamentos.columns:
                df_cancelamentos = df_cancelamentos.sort_values(by='data_cancelamento', ascending=False)
            
            # Remover duplicatas por chassi (Mantendo o mais recente/primeiro após sort)
            df_limpo = df_cancelamentos.drop_duplicates(subset=['chassi'], keep='first')
            
            count_cancelados = len(df_limpo)
            print(f"   Cancelados únicos finais: {count_cancelados}")

        resultados.append({'data': dia_x, 'cancelados': count_cancelados})

    except Exception as e:
        print(f"   ERRO CRÍTICO no dia {dia_x}: {e}")
        resultados.append({'data': dia_x, 'cancelados': 0, 'erro': str(e)})

# --- 5. RESULTADO ---
df_final = pd.DataFrame(resultados)
print("\n--- Relatório Final de Cancelamentos ---")
print(df_final)