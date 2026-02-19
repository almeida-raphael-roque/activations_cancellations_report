import duckdb
import boto3
import pandas as pd
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÕES E CREDENCIAIS ---
BUCKET = "transdesk-develop-bronze"
DATA_INICIO = "2025-08-01"
DATA_FIM = "2026-02-17"

SCHEMAS = {
    'silver': 'vilesoft',
    'stcoop': 'stcoop',
    'viavante': 'viavante',
    'tag': 'tag'
}

TABELAS = [
    "insurance_registration", "insurance_reg_set", "cliente", "catalogo", 
    "representante", "insurance_status", "insurance_reg_set_coverage", 
    "insurance_vehicle", "tipo_veiculo", "insurance_reg_set_cov_trailer", 
    "insurance_trailer", "vendedor", "price_list_benefits", "type_category", 
    "category", "benefits", "web_user"
]

# --- 2. INICIALIZAÇÃO DO DUCKDB ---
region = "sa-east-1"
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
    con.execute("SET s3_endpoint='s3.sa-east-1.amazonaws.com';")


session = boto3.Session(region_name=region)
creds = session.get_credentials()
if not creds:
    raise Exception("Não foi possível encontrar credenciais AWS. Verifique seu login (aws sso login ou chaves).")
creds = creds.get_frozen_credentials()
aplicar_credenciais_duckdb(con, region, creds)

s3 = session.client("s3")

def listar_parquets_s3(bucket_name: str, prefix_path: str) -> list[str]:
    urls = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix_path):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".parquet"):
                urls.append(f"s3://{bucket_name}/{obj['Key']}")
    return urls

def uma_url_parquet_qualquer(bucket_name: str, s3_folder: str, tb: str):
    prefix = f"{s3_folder}/{tb.lower()}/"
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix, PaginationConfig={"MaxItems": 10}):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".parquet"):
                return f"s3://{bucket_name}/{obj['Key']}"
    return None

for sql_schema_name in SCHEMAS.keys():
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {sql_schema_name};")

# --- 3. SQL QUERY ---
QUERY_BASE = """
WITH base_unificada AS (
    SELECT coalesce(iv.chassi, it.chassi, itt.chassi) AS chassi,
           CAST(COALESCE(irs.DATE_INITAL_EFFECT, irs.DATE_FINAL_EFFECT - INTERVAL '364 days') AS DATE) AS inicio_vig,
           cata.fantasia AS unidade
    FROM silver.insurance_registration ir
    LEFT JOIN silver.insurance_reg_set irs ON irs.parent = ir.id
    LEFT JOIN silver.insurance_reg_set_coverage irsc ON irsc.parent = irs.id
    LEFT JOIN silver.insurance_vehicle iv ON iv.id = irsc.id_vehicle
    LEFT JOIN silver.insurance_reg_set_cov_trailer irsct ON irsct.parent = irsc.id
    LEFT JOIN silver.insurance_trailer it ON it.id = irsct.id_trailer
    LEFT JOIN silver.insurance_trailer itt ON itt.id = irsc.id_trailer
    LEFT JOIN silver.insurance_status iss ON iss.id = irs.id_status
    LEFT JOIN silver.insurance_status isss ON isss.id = irsc.id_status
    LEFT JOIN silver.representante r ON r.codigo = irs.id_unity
    LEFT JOIN silver.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
    WHERE iss.id = 7 AND isss.description = 'ATIVO'
    UNION ALL
    SELECT coalesce(iv.chassi, it.chassi, itt.chassi) AS chassi,
           CAST(COALESCE(irs.DATE_INITAL_EFFECT, irs.DATE_FINAL_EFFECT - INTERVAL '364 days') AS DATE) AS inicio_vig,
           cata.fantasia AS unidade
    FROM stcoop.insurance_registration ir
    LEFT JOIN stcoop.insurance_reg_set irs ON irs.parent = ir.id
    LEFT JOIN stcoop.insurance_reg_set_coverage irsc ON irsc.parent = irs.id
    LEFT JOIN stcoop.insurance_vehicle iv ON iv.id = irsc.id_vehicle
    LEFT JOIN stcoop.insurance_reg_set_cov_trailer irsct ON irsct.parent = irsc.id
    LEFT JOIN stcoop.insurance_trailer it ON it.id = irsct.id_trailer
    LEFT JOIN stcoop.insurance_trailer itt ON itt.id = irsc.id_trailer
    LEFT JOIN stcoop.insurance_status iss ON iss.id = irs.id_status
    LEFT JOIN stcoop.insurance_status isss ON isss.id = irsc.id_status
    LEFT JOIN stcoop.representante r ON r.codigo = irs.id_unity
    LEFT JOIN stcoop.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
    WHERE iss.id = 7 AND isss.description = 'ATIVO'
    UNION ALL
    SELECT coalesce(iv.chassi, it.chassi, itt.chassi) AS chassi,
           CAST(COALESCE(irs.DATE_INITAL_EFFECT, irs.DATE_FINAL_EFFECT - INTERVAL '364 days') AS DATE) AS inicio_vig,
           cata.fantasia AS unidade
    FROM viavante.insurance_registration ir
    LEFT JOIN viavante.insurance_reg_set irs ON irs.parent = ir.id
    LEFT JOIN viavante.insurance_reg_set_coverage irsc ON irsc.parent = irs.id
    LEFT JOIN viavante.insurance_vehicle iv ON iv.id = irsc.id_vehicle
    LEFT JOIN viavante.insurance_reg_set_cov_trailer irsct ON irsct.parent = irsc.id
    LEFT JOIN viavante.insurance_trailer it ON it.id = irsct.id_trailer
    LEFT JOIN viavante.insurance_trailer itt ON itt.id = irsc.id_trailer
    LEFT JOIN viavante.insurance_status iss ON iss.id = irs.id_status
    LEFT JOIN viavante.insurance_status isss ON isss.id = irsc.id_status
    LEFT JOIN viavante.representante r ON r.codigo = irs.id_unity
    LEFT JOIN viavante.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
    WHERE iss.id = 7 AND isss.description = 'ATIVO'
    UNION ALL
    SELECT coalesce(iv.chassi, it.chassi, itt.chassi) AS chassi,
           CAST(COALESCE(irs.DATE_INITAL_EFFECT, irs.DATE_FINAL_EFFECT - INTERVAL '364 days') AS DATE) AS inicio_vig,
           cata.fantasia AS unidade
    FROM tag.insurance_registration ir
    LEFT JOIN tag.insurance_reg_set irs ON irs.parent = ir.id
    LEFT JOIN tag.insurance_reg_set_coverage irsc ON irsc.parent = irs.id
    LEFT JOIN tag.insurance_vehicle iv ON iv.id = irsc.id_vehicle
    LEFT JOIN tag.insurance_reg_set_cov_trailer irsct ON irsct.parent = irsc.id
    LEFT JOIN tag.insurance_trailer it ON it.id = irsct.id_trailer
    LEFT JOIN tag.insurance_trailer itt ON itt.id = irsc.id_trailer
    LEFT JOIN tag.insurance_status iss ON iss.id = irs.id_status
    LEFT JOIN tag.insurance_status isss ON isss.id = irsc.id_status
    LEFT JOIN tag.representante r ON r.codigo = irs.id_unity
    LEFT JOIN tag.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
    WHERE iss.id = 7 AND isss.description = 'ATIVO'
)
SELECT * FROM base_unificada
"""

# --- 4. LOOP DE EXECUÇÃO ---
resultados = []

def daterange(start_date, end_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    for n in range(int((end - start).days) + 1):
        yield start + timedelta(n)

print(f"Iniciando loop de {DATA_INICIO} a {DATA_FIM}...")

for today in daterange(DATA_INICIO, DATA_FIM):
    dia_str = today.strftime("%Y-%m-%d")
    yesterday = today - timedelta(days=1)
    print(f"-> Processando dia de referência: {dia_str}")

    # Renova credenciais a cada dia (evita token SSO expirado no meio do loop)
    creds_dia = session.get_credentials()
    if creds_dia:
        creds_dia = creds_dia.get_frozen_credentials()
        aplicar_credenciais_duckdb(con, region, creds_dia)

    # Montar Views para o dia processado
    criadas_com_dados = set()
    for sql_name, s3_folder in SCHEMAS.items():
        for tb in TABELAS:
            prefix = f"{s3_folder}/{tb.lower()}/landing_date={dia_str}/"
            urls = listar_parquets_s3(BUCKET, prefix)
            if urls:
                try:
                    paths_sql = ", ".join(repr(u) for u in urls)
                    con.execute(f"CREATE OR REPLACE VIEW {sql_name}.{tb} AS SELECT * FROM read_parquet([{paths_sql}])")
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
                    print(f"   Erro ao criar view vazia {sql_name}.{tb} a partir de schema existente:", exc)
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
        df_ativos = con.execute(QUERY_BASE).df()

        # Filtrar apenas pelas unidades especificadas
        unidades_permitidas = [
'TRANSDESK DIGITAL LTDA'
        ]
        
        # Filtrar apenas pelas unidades especificadas
        if not df_ativos.empty and 'unidade' in df_ativos.columns:
            df_ativos = df_ativos[df_ativos['unidade'].isin(unidades_permitidas)].copy()
        elif not df_ativos.empty:
            # Se não houver coluna 'unidade', considera vazio (nenhuma unidade permitida)
            df_ativos = pd.DataFrame()

        # Se após o filtro o dataframe estiver vazio, define 0 e continua
        if df_ativos.empty:
            total_ativados = 0
        else:
            df_ativos['inicio_vig'] = pd.to_datetime(df_ativos['inicio_vig']).dt.date

            # Ordenar por data (inicio_vig) decrescente primeiro, depois remover duplicatas por chassi
            df_ativos = df_ativos.sort_values('inicio_vig', ascending=False)
            df_ativos = df_ativos.drop_duplicates(subset=['chassi'])

            
            if today.weekday() == 0: # Segunda-feira
                sexta = (today - timedelta(days=3)).date()
                domingo = (today - timedelta(days=1)).date()
                ativos_mask = (df_ativos['inicio_vig'] >= sexta) & (df_ativos['inicio_vig'] <= domingo)
            else:
                ativos_mask = (df_ativos['inicio_vig'] == yesterday.date())

            total_ativados = len(df_ativos[ativos_mask])

        print(f"   Total Ativados: {total_ativados}")
        resultados.append({'data': dia_str, 'total_ativados': total_ativados})

    except Exception as e:
        print(f"   ERRO no dia {dia_str}: {e}")
        resultados.append({'data': dia_str, 'total_ativados': 0, 'erro': str(e)})

# --- 5. RESULTADO ---
df_final = pd.DataFrame(resultados)
print("\n--- Relatório Final ---")
print(df_final)