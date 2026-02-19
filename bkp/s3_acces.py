import duckdb
import boto3
import pandas as pd

# --- 1. DEFINIR O CAMINHO EXATO (bucket em sa-east-1) ---
bucket = "transdesk-develop-bronze"
region = "sa-east-1"
prefix = "viavante/insurance_reg_set/landing_date=2024-07-30/"
caminho_teste = f"s3://{bucket}/{prefix}*.parquet"

print(f"Tentando acessar: {caminho_teste}")

# --- 2. CONFIGURAR DUCKDB ---
try:
    con = duckdb.connect(database=':memory:')
    con.execute("INSTALL httpfs; LOAD httpfs;")

    session = boto3.Session(region_name=region)
    creds = session.get_credentials()
    if not creds:
        raise Exception("Não foi possível encontrar credenciais AWS. Verifique seu login (aws sso login ou chaves).")
    creds = creds.get_frozen_credentials()

    # Região e credenciais (token só se existir — SSO usa token, IAM user não)
    sets = [
        f"SET s3_region='{region}';",
        f"SET s3_access_key_id='{creds.access_key}';",
        f"SET s3_secret_access_key='{creds.secret_key}';",
    ]
    if getattr(creds, "token", None):
        sets.append(f"SET s3_session_token='{creds.token}';")
    con.execute("\n".join(sets))

    # Endpoint explícito para sa-east-1 (evita 400 em alguns clientes)
    con.execute("SET s3_endpoint='s3.sa-east-1.amazonaws.com';")

    # --- 3. TENTAR LER (duas estratégias) ---
    df_teste = None

    # Estratégia A: Listar com boto3 e passar URLs ao DuckDB (evita LIST do httpfs que dava 400)
    s3 = session.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    urls = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".parquet"):
                urls.append(f"s3://{bucket}/{key}")
    if urls:
        # read_parquet aceita lista de caminhos (evita LIST do httpfs que gerava 400)
        paths_sql = ", ".join(repr(u) for u in urls)
        query = f"SELECT * FROM read_parquet([{paths_sql}]) LIMIT 5"
        df_teste = con.execute(query).df()
        print("\n✅ SUCESSO (via listagem boto3 + read_parquet).")
    else:
        # Nenhum parquet no prefixo: tenta wildcard direto (endpoint/region podem resolver)
        query = f"SELECT * FROM read_parquet('{caminho_teste}', hive_partitioning=1) LIMIT 5"
        df_teste = con.execute(query).df()
        print("\n✅ SUCESSO (via wildcard S3).")

    if df_teste is not None:
        print(f"Colunas encontradas: {list(df_teste.columns)}")
        print("\nAmostra dos dados:")
        try:
            from IPython.display import display
            display(df_teste)
        except ImportError:
            print(df_teste)

except Exception as e:
    print("\n❌ ERRO DE ACESSO:")
    print(e)
    print("\nDica: Verifique se você está logado na AWS e se tem permissão de leitura nesse bucket.")