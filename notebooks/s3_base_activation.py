import duckdb
import boto3
import pandas as pd
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÕES E CREDENCIAIS ---
BUCKET = "transdesk-develop-bronze"
DATA_INICIO = "2025-01-09"
DATA_FIM = "2026-02-01"

# AQUI ESTÁ O AJUSTE SOLICITADO:
# Esquerda (Chave): Como está escrito no seu SQL (ex: FROM silver.tabela)
# Direita (Valor): Nome da pasta real no S3 (ex: vilesoft/tabela)
SCHEMAS = {
    'silver': 'vilesoft',   # <--- Mapeamento: SQL chama de silver, mas busca na pasta vilesoft
    'stcoop': 'stcoop',
    'viavante': 'viavante',
    'tag': 'tag'
}

# Lista de tabelas necessárias
TABELAS = [
    "insurance_registration", "insurance_reg_set", "cliente", "catalogo", 
    "representante", "insurance_status", "insurance_reg_set_coverage", 
    "insurance_vehicle", "tipo_veiculo", "insurance_reg_set_cov_trailer", 
    "insurance_trailer", "vendedor", "price_list_benefits", "type_category", 
    "category", "benefits", "web_user"
]

# --- 2. INICIALIZAÇÃO DO DUCKDB (exatamente a mesma lógica do s3_acces.py) ---
region = "sa-east-1"
bucket = BUCKET

con = duckdb.connect(database=':memory:')
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")


def aplicar_credenciais_duckdb(con, region: str, creds):
    """Aplica credenciais AWS ao DuckDB (útil para renovar token SSO a cada dia)."""
    sets = [
        f"SET s3_region='{region}';",
        f"SET s3_access_key_id='{creds.access_key}';",
        f"SET s3_secret_access_key='{creds.secret_key}';",
    ]
    if getattr(creds, "token", None):
        sets.append(f"SET s3_session_token='{creds.token}';")
    con.execute("\n".join(sets))


session = boto3.Session(region_name=region)
creds = session.get_credentials()
if not creds:
    raise Exception("Não foi possível encontrar credenciais AWS. Verifique seu login (aws sso login ou chaves).")
creds = creds.get_frozen_credentials()
aplicar_credenciais_duckdb(con, region, creds)

# Endpoint explícito para sa-east-1 (evita 400 em alguns clientes)
con.execute("SET s3_endpoint='s3.sa-east-1.amazonaws.com';")

# Cliente S3 para listar (igual s3_acces: boto3 faz LIST, DuckDB só faz GET)
s3 = session.client("s3")


def listar_parquets_s3(bucket_name: str, prefix_path: str) -> list[str]:
    """Lista URLs s3:// com boto3 (igual s3_acces.py — evita LIST do httpfs que dava 400)."""
    urls = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix_path):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".parquet"):
                urls.append(f"s3://{bucket_name}/{key}")
    return urls


def uma_url_parquet_qualquer(bucket_name: str, s3_folder: str, tb: str):
    """Retorna uma URL de parquet para (folder, tb) em qualquer landing_date (para view vazia com schema)."""
    prefix = f"{s3_folder}/{tb.lower()}/"
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix, PaginationConfig={"MaxItems": 10}):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".parquet"):
                return f"s3://{bucket_name}/{key}"
    return None

# Cria os schemas no DuckDB para o SQL funcionar
for sql_schema_name in SCHEMAS.keys():
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {sql_schema_name};")

# --- 3. SEU SQL ORIGINAL (Mantendo nomes antigos como 'silver') ---
QUERY_BASE = """
WITH base_unificada AS (
    -- BLOCO SILVER
    SELECT 
        coalesce(iv.BOARD, it.BOARD, itt.BOARD) AS placa,
        coalesce(iv.chassi, it.chassi, itt.chassi) AS chassi,
        ir.id AS matricula,
        cata.fantasia AS unidade,
        iss.description AS status_conjunto,
        cat.nome AS cliente,
        CAST(
            COALESCE(
                irs.DATE_INITAL_EFFECT, 
                irs.DATE_FINAL_EFFECT - INTERVAL '364 days'
            ) AS DATE
        ) AS inicio_vig,
        CAST(irs.date_activation AS DATE) AS data_ativacao,
        'Segtruck' AS empresa
    FROM silver.insurance_registration ir
        LEFT JOIN silver.insurance_reg_set irs ON irs.parent = ir.id
        LEFT JOIN silver.cliente clie ON clie.codigo = ir.CUSTOMER_ID
        LEFT JOIN silver.catalogo cat ON cat.cnpj_cpf = clie.cnpj_cpf
        LEFT JOIN silver.representante r ON r.codigo = irs.id_unity
        LEFT JOIN silver.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
        LEFT JOIN silver.insurance_status iss ON iss.id = irs.id_status
        LEFT JOIN silver.insurance_reg_set_coverage irsc ON irsc.parent = irs.id
        LEFT JOIN silver.insurance_vehicle iv ON iv.id = irsc.id_vehicle
        LEFT JOIN silver.insurance_reg_set_cov_trailer irsct ON irsct.parent = irsc.id
        LEFT JOIN silver.insurance_trailer it ON it.id = irsct.id_trailer
        LEFT JOIN silver.insurance_trailer itt ON itt.id = irsc.id_trailer
        LEFT JOIN silver.insurance_status isss ON isss.id = irsc.id_status
    WHERE iss.id = 7
      AND coalesce(iv.BOARD, it.BOARD, itt.BOARD) IS NOT NULL
      AND coalesce(iv.chassi, it.chassi, itt.chassi) IS NOT NULL
      AND isss.description = 'ATIVO'

    UNION ALL

    -- BLOCO STCOOP
    SELECT 
        coalesce(iv.BOARD, it.BOARD, itt.BOARD) AS placa,
        coalesce(iv.chassi, it.chassi, itt.chassi) AS chassi,
        ir.id AS matricula,
        cata.fantasia AS unidade,
        iss.description AS status_conjunto,
        cat.nome AS cliente,
        CAST(
            COALESCE(
                irs.DATE_INITAL_EFFECT, 
                irs.DATE_FINAL_EFFECT - INTERVAL '364 days'
            ) AS DATE
        ) AS inicio_vig,
        CAST(irs.date_activation AS DATE) AS data_ativacao,
        'Stcoop' AS empresa
    FROM stcoop.insurance_registration ir
        LEFT JOIN stcoop.insurance_reg_set irs ON irs.parent = ir.id
        LEFT JOIN stcoop.cliente clie ON clie.codigo = ir.CUSTOMER_ID
        LEFT JOIN stcoop.catalogo cat ON cat.cnpj_cpf = clie.cnpj_cpf
        LEFT JOIN stcoop.representante r ON r.codigo = irs.id_unity
        LEFT JOIN stcoop.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
        LEFT JOIN stcoop.insurance_status iss ON iss.id = irs.id_status
        LEFT JOIN stcoop.insurance_reg_set_coverage irsc ON irsc.parent = irs.id
        LEFT JOIN stcoop.insurance_vehicle iv ON iv.id = irsc.id_vehicle
        LEFT JOIN stcoop.insurance_reg_set_cov_trailer irsct ON irsct.parent = irsc.id
        LEFT JOIN stcoop.insurance_trailer it ON it.id = irsct.id_trailer
        LEFT JOIN stcoop.insurance_trailer itt ON itt.id = irsc.id_trailer
        LEFT JOIN stcoop.insurance_status isss ON isss.id = irsc.id_status
    WHERE iss.id = 7
      AND coalesce(iv.BOARD, it.BOARD, itt.BOARD) IS NOT NULL
      AND coalesce(iv.chassi, it.chassi, itt.chassi) IS NOT NULL
      AND isss.description = 'ATIVO'

    UNION ALL

    -- BLOCO VIAVANTE
    SELECT 
        coalesce(iv.BOARD, it.BOARD, itt.BOARD) AS placa,
        coalesce(iv.chassi, it.chassi, itt.chassi) AS chassi,
        ir.id AS matricula,
        cata.fantasia AS unidade,
        iss.description AS status_conjunto,
        cat.nome AS cliente,
        CAST(
            COALESCE(
                irs.DATE_INITAL_EFFECT, 
                irs.DATE_FINAL_EFFECT - INTERVAL '364 days'
            ) AS DATE
        ) AS inicio_vig,
        CAST(irs.date_activation AS DATE) AS data_ativacao,
        'Viavante' AS empresa
    FROM viavante.insurance_registration ir
        LEFT JOIN viavante.insurance_reg_set irs ON irs.parent = ir.id
        LEFT JOIN viavante.cliente clie ON clie.codigo = ir.CUSTOMER_ID
        LEFT JOIN viavante.catalogo cat ON cat.cnpj_cpf = clie.cnpj_cpf
        LEFT JOIN viavante.representante r ON r.codigo = irs.id_unity
        LEFT JOIN viavante.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
        LEFT JOIN viavante.insurance_status iss ON iss.id = irs.id_status
        LEFT JOIN viavante.insurance_reg_set_coverage irsc ON irsc.parent = irs.id
        LEFT JOIN viavante.insurance_vehicle iv ON iv.id = irsc.id_vehicle
        LEFT JOIN viavante.insurance_reg_set_cov_trailer irsct ON irsct.parent = irsc.id
        LEFT JOIN viavante.insurance_trailer it ON it.id = irsct.id_trailer
        LEFT JOIN viavante.insurance_trailer itt ON itt.id = irsc.id_trailer
        LEFT JOIN viavante.insurance_status isss ON isss.id = irsc.id_status
    WHERE iss.id = 7
      AND coalesce(iv.BOARD, it.BOARD, itt.BOARD) IS NOT NULL
      AND coalesce(iv.chassi, it.chassi, itt.chassi) IS NOT NULL
      AND isss.description = 'ATIVO'

    UNION ALL

    -- BLOCO TAG
    SELECT 
        coalesce(iv.BOARD, it.BOARD, itt.BOARD) AS placa,
        coalesce(iv.chassi, it.chassi, itt.chassi) AS chassi,
        ir.id AS matricula,
        cata.fantasia AS unidade,
        iss.description AS status_conjunto,
        cat.nome AS cliente,
        CAST(
            COALESCE(
                irs.DATE_INITAL_EFFECT, 
                irs.DATE_FINAL_EFFECT - INTERVAL '364 days'
            ) AS DATE
        ) AS inicio_vig,
        CAST(irs.date_activation AS DATE) AS data_ativacao,
        'Tag' AS empresa
    FROM tag.insurance_registration ir
        LEFT JOIN tag.insurance_reg_set irs ON irs.parent = ir.id
        LEFT JOIN tag.cliente clie ON clie.codigo = ir.CUSTOMER_ID
        LEFT JOIN tag.catalogo cat ON cat.cnpj_cpf = clie.cnpj_cpf
        LEFT JOIN tag.representante r ON r.codigo = irs.id_unity
        LEFT JOIN tag.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
        LEFT JOIN tag.insurance_status iss ON iss.id = irs.id_status
        LEFT JOIN tag.insurance_reg_set_coverage irsc ON irsc.parent = irs.id
        LEFT JOIN tag.insurance_vehicle iv ON iv.id = irsc.id_vehicle
        LEFT JOIN tag.insurance_reg_set_cov_trailer irsct ON irsct.parent = irsc.id
        LEFT JOIN tag.insurance_trailer it ON it.id = irsct.id_trailer
        LEFT JOIN tag.insurance_trailer itt ON itt.id = irsc.id_trailer
        LEFT JOIN tag.insurance_status isss ON isss.id = irsc.id_status
    WHERE iss.id = 7
      AND coalesce(iv.BOARD, it.BOARD, itt.BOARD) IS NOT NULL
      AND coalesce(iv.chassi, it.chassi, itt.chassi) IS NOT NULL
      AND isss.description = 'ATIVO'
)
SELECT * FROM base_unificada
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

    # Renova credenciais a cada dia (evita token SSO expirado no meio do loop)
    creds_dia = session.get_credentials()
    if creds_dia:
        creds_dia = creds_dia.get_frozen_credentials()
        aplicar_credenciais_duckdb(con, region, creds_dia)

    # Montar Views (Ligação entre SQL e S3)
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
                    print(f"   Erro ao criar view {sql_name}.{tb} com dados ({len(urls)} arquivos):", exc)

    # Views vazias copiando schema de outra schema que tenha a tabela
    for sql_name, s3_folder in SCHEMAS.items():
        for tb in TABELAS:
            if (sql_name, tb) in criadas_com_dados:
                continue
            ref = None
            for outro in SCHEMAS.keys():
                if (outro, tb) in criadas_com_dados:
                    ref = outro
                    break
            if ref is not None:
                try:
                    con.execute(f"""
                        CREATE OR REPLACE VIEW {sql_name}.{tb} AS 
                        SELECT * FROM {ref}.{tb} WHERE 1=0
                    """)
                except Exception as exc:
                    print("   Erro ao criar view vazia a partir de schema existente:", exc)
            else:
                # Nenhuma schema tem essa tabela com dados: pega 1 parquet de qualquer data para ter o schema
                uma_url = uma_url_parquet_qualquer(BUCKET, s3_folder, tb)
                if uma_url is not None:
                    try:
                        con.execute(f"""
                            CREATE OR REPLACE VIEW {sql_name}.{tb} AS 
                            SELECT * FROM read_parquet([{repr(uma_url)}]) WHERE 1=0
                        """)
                    except Exception as exc:
                        print(f"   Erro ao criar view vazia {sql_name}.{tb} a partir de S3 (acesso?):", exc)
                else:
                    # Pasta S3 vazia ou inexistente: copia schema de qualquer outra schema que já tenha a tabela
                    for outro in SCHEMAS.keys():
                        if outro == sql_name:
                            continue
                        try:
                            con.execute(f"""
                                CREATE OR REPLACE VIEW {sql_name}.{tb} AS 
                                SELECT * FROM {outro}.{tb} WHERE 1=0
                            """)
                            break
                        except Exception:
                            continue

    try:
        # Extrair dados (SQL)
        df_dia = con.execute(QUERY_BASE).df()

        if df_dia.empty:
            count_ativos = 0
            print("   Nenhum dado bruto encontrado.")
        else:
            df_dia['inicio_vig'] = pd.to_datetime(df_dia['inicio_vig'], errors='coerce')
            df_dia = df_dia.sort_values(by='inicio_vig', ascending=False)
            df_limpo = df_dia.drop_duplicates(subset=['chassi'], keep='first')
            count_ativos = len(df_limpo)
            print(f"   Ativos finais: {count_ativos}")

        resultados.append({'data': dia_x, 'ativos': count_ativos})

    except Exception as e:
        print(f"   ERRO CRÍTICO no dia {dia_x}: {e}")
        resultados.append({'data': dia_x, 'ativos': 0, 'erro': str(e)})

# --- 5. RESULTADO ---
df_final = pd.DataFrame(resultados)
print("\n--- Relatório Final ---")
print(df_final)