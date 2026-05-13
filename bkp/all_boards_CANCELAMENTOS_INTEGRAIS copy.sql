WITH CTE_segtruck AS (
    SELECT
    -- DADOS DO VEÍCULO / REBOQUE
        coalesce(iv.BOARD,it.BOARD,itt.BOARD) as "placa",
        coalesce(iv.chassi,it.chassi,itt.chassi) as "chassi",
        coalesce(iv.id,it.id,itt.id) as "id_placa",
        coalesce(irsc.ID_VEHICLE) as "id_veiculo",
        coalesce(irsct.ID_TRAILER) as "id_carroceria",
    -- DADOS DO CONTRATO
        ir.id as "matricula",
        irs.id as "conjunto",
        cata.fantasia as "unidade",
        v.DESCRICAO as "consultor",
        iss.description as "status",
        cat.nome as "cliente",
        user_name.suporte as "usuario_suporte",
        irs.user_name_cancellation as "usuario_cancelamento",
    -- DADOS DO PRODUTO
        irsc.id as "coverage_id",
        b.description as "beneficio",
        isss.description as "status_beneficio",
    -- DADOS DE DATAS
        current_date AS "data_extracao",
        irs.data_registration  as "data_registro",
        cast(coalesce(irs.DATE_INITAL_EFFECT,date_add('day', -364, irs.DATE_FINAL_EFFECT)) as date) as "data_ativacao",
        cast(coalesce(irsc.date_initial_effect,date_add('day', -364, irsc.date_final_effect)) as date) as "data_ativacao_beneficio",
        cast(irs.date_cancellation as date) as "data_cancelamento",
    -- DADOS DE ORDENAMENTO
        ROW_NUMBER() OVER (PARTITION BY coalesce(iv.chassi,it.chassi,itt.chassi) ORDER BY irs.data_registration DESC) as "rn",
    -- DADOS DA EMPRESA
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
        AND iss.description NOT IN ('ATIVO', 'RENOVACAO')

),

CTE_stcoop AS (
    SELECT
    -- DADOS DO VEÍCULO / REBOQUE
        coalesce(iv.BOARD,it.BOARD,itt.BOARD) as "placa",
        coalesce(iv.chassi,it.chassi,itt.chassi) as "chassi",
        coalesce(iv.id,it.id,itt.id) as "id_placa",
        coalesce(irsc.ID_VEHICLE) as "id_veiculo",
        coalesce(irsct.ID_TRAILER) as "id_carroceria",
    -- DADOS DO CONTRATO
        ir.id as "matricula",
        irs.id as "conjunto",
        cata.fantasia as "unidade",
        v.DESCRICAO as "consultor",
        iss.description as "status",
        cat.nome as "cliente",
        user_name.suporte as "usuario_suporte",
        irs.user_name_cancellation as "usuario_cancelamento",
    -- DADOS DO PRODUTO
        irsc.id as "coverage_id",
        b.description as "beneficio",
        isss.description as "status_beneficio",
    -- DADOS DE DATAS
        current_date AS "data_extracao",
        irs.data_registration  as "data_registro",
        cast(coalesce(irs.DATE_INITAL_EFFECT,date_add('day', -364, irs.DATE_FINAL_EFFECT)) as date) as "data_ativacao",
        cast(coalesce(irsc.date_initial_effect,date_add('day', -364, irsc.date_final_effect)) as date) as "data_ativacao_beneficio",
        cast(irs.date_cancellation as date) as "data_cancelamento",
    -- DADOS DE ORDENAMENTO
        ROW_NUMBER() OVER (PARTITION BY coalesce(iv.chassi,it.chassi,itt.chassi) ORDER BY irs.data_registration DESC) as "rn",
    -- DADOS DA EMPRESA
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
        AND iss.description NOT IN ('ATIVO', 'RENOVACAO')

),

CTE_viavante AS (
    SELECT
    -- DADOS DO VEÍCULO / REBOQUE
        coalesce(iv.BOARD,it.BOARD,itt.BOARD) as "placa",
        coalesce(iv.chassi,it.chassi,itt.chassi) as "chassi",
        coalesce(iv.id,it.id,itt.id) as "id_placa",
        coalesce(irsc.ID_VEHICLE) as "id_veiculo",
        coalesce(irsct.ID_TRAILER) as "id_carroceria",
    -- DADOS DO CONTRATO
        ir.id as "matricula",
        irs.id as "conjunto",
        cata.fantasia as "unidade",
        v.DESCRICAO as "consultor",
        iss.description as "status",
        cat.nome as "cliente",
        user_name.suporte as "usuario_suporte",
        irs.user_name_cancellation as "usuario_cancelamento",
    -- DADOS DO PRODUTO
        irsc.id as "coverage_id",
        b.description as "beneficio",
        isss.description as "status_beneficio",
    -- DADOS DE DATAS
        current_date AS "data_extracao",
        irs.data_registration  as "data_registro",
        cast(coalesce(irs.DATE_INITAL_EFFECT,date_add('day', -364, irs.DATE_FINAL_EFFECT)) as date) as "data_ativacao",
        cast(coalesce(irsc.date_initial_effect,date_add('day', -364, irsc.date_final_effect)) as date) as "data_ativacao_beneficio",
        cast(irs.date_cancellation as date) as "data_cancelamento",
    -- DADOS DE ORDENAMENTO
        ROW_NUMBER() OVER (PARTITION BY coalesce(iv.chassi,it.chassi,itt.chassi) ORDER BY irs.data_registration DESC) as "rn",
    -- DADOS DA EMPRESA
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
        AND iss.description NOT IN ('ATIVO', 'RENOVACAO')
),

CTE_tag AS (
    SELECT
    -- DADOS DO VEÍCULO / REBOQUE
        coalesce(iv.BOARD,it.BOARD,itt.BOARD) as "placa",
        coalesce(iv.chassi,it.chassi,itt.chassi) as "chassi",
        coalesce(iv.id,it.id,itt.id) as "id_placa",
        coalesce(irsc.ID_VEHICLE) as "id_veiculo",
        coalesce(irsct.ID_TRAILER) as "id_carroceria",
    -- DADOS DO CONTRATO
        ir.id as "matricula",
        irs.id as "conjunto",
        cata.fantasia as "unidade",
        v.DESCRICAO as "consultor",
        iss.description as "status",
        cat.nome as "cliente",
        user_name.suporte as "usuario_suporte",
        irs.user_name_cancellation as "usuario_cancelamento",
    -- DADOS DO PRODUTO
        irsc.id as "coverage_id",
        b.description as "beneficio",
        isss.description as "status_beneficio",
    -- DADOS DE DATAS
        current_date AS "data_extracao",
        irs.data_registration  as "data_registro",
        cast(coalesce(irs.DATE_INITAL_EFFECT,date_add('day', -364, irs.DATE_FINAL_EFFECT)) as date) as "data_ativacao",
        cast(coalesce(irsc.date_initial_effect,date_add('day', -364, irsc.date_final_effect)) as date) as "data_ativacao_beneficio",
        cast(irs.date_cancellation as date) as "data_cancelamento",
    -- DADOS DE ORDENAMENTO
        ROW_NUMBER() OVER (PARTITION BY coalesce(iv.chassi,it.chassi,itt.chassi) ORDER BY irs.data_registration DESC) as "rn",
    -- DADOS DA EMPRESA
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
        AND iss.description NOT IN ('ATIVO', 'RENOVACAO')
)

SELECT 
    "placa",
    "chassi",
    "id_placa",
    "id_veiculo",
    "id_carroceria",
    "matricula",
    "conjunto",
    "unidade",
    "consultor",
    "status",
    "cliente",
    "usuario_suporte",
    "usuario_cancelamento",
    "coverage_id",
    "beneficio",
    "status_beneficio",
    "data_extracao",
    "data_registro",
    "data_ativacao",
    "data_ativacao_beneficio",
    "data_cancelamento",
    "empresa"
FROM (
    SELECT * FROM CTE_segtruck WHERE rn = 1
    UNION ALL
    SELECT * FROM CTE_stcoop WHERE rn = 1
    UNION ALL
    SELECT * FROM CTE_viavante WHERE rn = 1
    UNION ALL
    SELECT * FROM CTE_tag WHERE rn = 1
) AS final

Where 
data_cancelamento >= date('2025-01-01')
