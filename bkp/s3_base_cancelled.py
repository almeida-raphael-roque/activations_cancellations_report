import duckdb
import boto3
import pandas as pd
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÕES E CREDENCIAIS ---
BUCKET = "transdesk-develop-bronze"
DATA_INICIO = "2026-02-13"
DATA_FIM = "2026-02-20"

SCHEMAS = {
    'silver': 'vilesoft',
    'stcoop': 'stcoop',
    'viavante': 'viavante',
    'tag': 'tag'
}

# Adicione aqui todas as tabelas necessárias para as queries de cancelamento
TABELAS = [
    "insurance_registration", "insurance_reg_set", "insurance_reg_set_coverage", 
    "insurance_vehicle", "insurance_trailer", "insurance_reg_set_cov_trailer",
    "insurance_status" # Certifique-se que todas as tabelas do SQL estejam aqui
]

region = "sa-east-1"
con = duckdb.connect(database=':memory:')
con.execute("INSTALL httpfs; LOAD httpfs;")

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

# Cliente S3 para listar (boto3 faz LIST, DuckDB só faz GET)
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
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix, PaginationConfig={"MaxItems": 5}):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".parquet"): return f"s3://{bucket_name}/{obj['Key']}"
    return None

for sql_schema_name in SCHEMAS.keys():
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {sql_schema_name};")

# --- 3. SQL QUERIES (ADAPTADAS PARA CANCELADOS) ---

# Exemplo genérico: Ajuste as colunas conforme sua necessidade real
SELECT_TEMPLATE = """
    SELECT 
        coalesce(iv.chassi, it.chassi, itt.chassi) AS chassi,
        CAST(irs.DATE_FINAL_EFFECT AS DATE) AS data_cancelamento
    FROM {schema}.insurance_registration ir
    LEFT JOIN {schema}.insurance_reg_set irs ON irs.parent = ir.id
    LEFT JOIN {schema}.insurance_reg_set_coverage irsc ON irsc.parent = irs.id
    LEFT JOIN {schema}.insurance_vehicle iv ON iv.id = irsc.id_vehicle
    LEFT JOIN {schema}.insurance_reg_set_cov_trailer irsct ON irsct.parent = irsc.id
    LEFT JOIN {schema}.insurance_trailer it ON it.id = irsct.id_trailer
    LEFT JOIN {schema}.insurance_trailer itt ON itt.id = irsc.id_trailer
    LEFT JOIN {schema}.insurance_status iss ON iss.id = irs.id_status
"""

# Montando as queries unificando os 4 schemas
QUERY_INTEGRAL = " UNION ALL ".join([SELECT_TEMPLATE.format(schema=s) + " WHERE iss.description = 'CANCELADO'" for s in SCHEMAS.keys()])
QUERY_PARCIAL  = " UNION ALL ".join([SELECT_TEMPLATE.format(schema=s) + " WHERE iss.description = 'CANCELADO_PARCIAL'" for s in SCHEMAS.keys()])

# --- 4. LOOP DE EXECUÇÃO ---
resultados = []

def daterange(start_date, end_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    for n in range(int((end - start).days) + 1):
        yield start + timedelta(n)

for today in daterange(DATA_INICIO, DATA_FIM):
    dia_str = today.strftime("%Y-%m-%d")
    yesterday = (today - timedelta(days=1)).date()

    # Renova credenciais a cada dia (evita token SSO expirado no meio do loop)
    creds_dia = session.get_credentials()
    if creds_dia:
        creds_dia = creds_dia.get_frozen_credentials()
        aplicar_credenciais_duckdb(con, region, creds_dia)

    # Criação das Views com dados do dia
    criadas_com_dados = set()
    for sql_name, s3_folder in SCHEMAS.items():
        for tb in TABELAS:
            prefix = f"{s3_folder}/{tb.lower()}/landing_date={dia_str}/"
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

    # Views vazias: quando um schema não tem dados naquele dia, cria view vazia para o SQL não quebrar
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
        # 1. Busca os dois DataFrames
        df_integrais = con.execute(QUERY_INTEGRAL).df()
        df_parciais = con.execute(QUERY_PARCIAL).df()

        # 2. Identificadores
        df_integrais['identificador'] = 'INTEGRAL'
        df_parciais['identificador'] = 'PARCIAL'

        # 3. Concatena e Formata Data
        df_cancelamentos = pd.concat([df_integrais, df_parciais], ignore_index=True)
        df_cancelamentos['data_cancelamento'] = pd.to_datetime(df_cancelamentos['data_cancelamento']).dt.date

        # 4. Ordena e Remove Duplicatas (Lógica solicitada)
        df_cancelamentos = df_cancelamentos.sort_values(by='data_cancelamento', ascending=False)
        df_cancelamentos = df_cancelamentos.drop_duplicates(subset=['chassi'], keep='first')

        # 5. Filtro de Data (Segunda-feira vs Dias Úteis)
        if today.weekday() == 0: # Segunda
            sexta = (today - timedelta(days=3)).date()
            domingo = (today - timedelta(days=1)).date()
            mask = (df_cancelamentos['data_cancelamento'] >= sexta) & (df_cancelamentos['data_cancelamento'] <= domingo)
        else:
            mask = (df_cancelamentos['data_cancelamento'] == yesterday)

        total_cancelados = len(df_cancelamentos[mask])
        resultados.append({'data': dia_str, 'total_cancelados': total_cancelados})
        print(f"{dia_str} -> Cancelados: {total_cancelados}")

    except Exception as e:
        print(f"Erro no dia {dia_str}: {e}")
        resultados.append({'data': dia_str, 'total_cancelados': 0, 'erro': str(e)})

# --- 5. RESULTADO FINAL ---
df_final = pd.DataFrame(resultados)
print(df_final)