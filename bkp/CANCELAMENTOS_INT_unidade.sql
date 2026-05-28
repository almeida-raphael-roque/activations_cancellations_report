SELECT
    CASE
        WHEN cata.nome LIKE '%FTR%' THEN cata.nome
        ELSE cata.fantasia
    END AS unidade,
    COUNT(DISTINCT coalesce(iv.board, it.board)) AS quantidade_placas,
    'Segtruck' as empresa
FROM silver.INSURANCE_REGISTRATION ir
    LEFT JOIN silver.CLIENTE cli ON cli.CODIGO = ir.CUSTOMER_ID
    LEFT JOIN silver.CATALOGO cat ON cat.CNPJ_CPF = cli.CNPJ_CPF
    LEFT JOIN silver.INSURANCE_REG_SET irs ON irs.PARENT = ir.ID
    LEFT JOIN silver.INSURANCE_STATUS iss ON iss.ID = irs.ID_STATUS
    LEFT JOIN silver.REPRESENTANTE r ON r.CODIGO = irs.ID_UNITY
    LEFT JOIN silver.CATALOGO cata ON cata.CNPJ_CPF = r.CNPJ_CPF
    LEFT JOIN silver.VENDEDOR v ON v.CODIGO = irs.ID_CONSULTANT
    LEFT JOIN silver.INSURANCE_REG_SET_COVERAGE irsc ON irsc.PARENT = irs.ID
    LEFT JOIN silver.PRICE_LIST_BENEFITS plb ON plb.ID = irsc.ID_PRICE_LIST
    LEFT JOIN silver.TYPE_CATEGORY tc ON tc.ID = plb.ID_TYPE_CATEGORY
    LEFT JOIN silver.CATEGORY c ON c.ID = tc.ID_CATEGORY
    LEFT JOIN silver.BENEFITS b ON b.ID = c.ID_BENEFITS
    LEFT JOIN silver.INSURANCE_VEHICLE iv ON iv.ID = irsc.ID_VEHICLE
    LEFT JOIN silver.TIPO_VEICULO tv ON tv.CODIGO = iv.CODE_TYPE_VEHICLE
    LEFT JOIN silver.INSURANCE_REG_SET_COV_TRAILER irsct ON irsct.PARENT = irsc.ID
    LEFT JOIN silver.INSURANCE_TRAILER it ON it.ID = irsct.ID_TRAILER
    LEFT JOIN silver.MARCA_VEICULO ma ON ma.CODIGO = iv.CODE_BRAND_VEHICLE
    LEFT JOIN silver.invoice i on i.id_set = irs.id
    LEFT JOIN silver.invoice_item ii on ii.parent = i.id
    LEFT JOIN silver.titulo_movimento tm on tm.id_titulo_movimento = ii.id_title_moviment
    left join silver.endereco en on en.cnpj_cpf = cli.cnpj_cpf
WHERE
    -- iss.description <> 'CANCELADO'
    cast(irs.date_cancellation AS date) = date('2025-11-19')
GROUP BY
    CASE
        WHEN cata.nome LIKE '%FTR%' THEN cata.nome
        ELSE cata.fantasia
    END

UNION ALL

SELECT
    CASE
        WHEN cata.nome LIKE '%FTR%' THEN cata.nome
        ELSE cata.fantasia
    END AS unidade,
    COUNT(DISTINCT coalesce(iv.board, it.board)) AS quantidade_placas,
    'Stcoop' as empresa
FROM stcoop.INSURANCE_REGISTRATION ir
    LEFT JOIN stcoop.CLIENTE cli ON cli.CODIGO = ir.CUSTOMER_ID
    LEFT JOIN stcoop.CATALOGO cat ON cat.CNPJ_CPF = cli.CNPJ_CPF
    LEFT JOIN stcoop.INSURANCE_REG_SET irs ON irs.PARENT = ir.ID
    LEFT JOIN stcoop.INSURANCE_STATUS iss ON iss.ID = irs.ID_STATUS
    LEFT JOIN stcoop.REPRESENTANTE r ON r.CODIGO = irs.ID_UNITY
    LEFT JOIN stcoop.CATALOGO cata ON cata.CNPJ_CPF = r.CNPJ_CPF
    LEFT JOIN stcoop.VENDEDOR v ON v.CODIGO = irs.ID_CONSULTANT
    LEFT JOIN stcoop.INSURANCE_REG_SET_COVERAGE irsc ON irsc.PARENT = irs.ID
    LEFT JOIN stcoop.PRICE_LIST_BENEFITS plb ON plb.ID = irsc.ID_PRICE_LIST
    LEFT JOIN stcoop.TYPE_CATEGORY tc ON tc.ID = plb.ID_TYPE_CATEGORY
    LEFT JOIN stcoop.CATEGORY c ON c.ID = tc.ID_CATEGORY
    LEFT JOIN stcoop.BENEFITS b ON b.ID = c.ID_BENEFITS
    LEFT JOIN stcoop.INSURANCE_VEHICLE iv ON iv.ID = irsc.ID_VEHICLE
    LEFT JOIN stcoop.TIPO_VEICULO tv ON tv.CODIGO = iv.CODE_TYPE_VEHICLE
    LEFT JOIN stcoop.INSURANCE_REG_SET_COV_TRAILER irsct ON irsct.PARENT = irsc.ID
    LEFT JOIN stcoop.INSURANCE_TRAILER it ON it.ID = irsct.ID_TRAILER
    LEFT JOIN stcoop.MARCA_VEICULO ma ON ma.CODIGO = iv.CODE_BRAND_VEHICLE
    LEFT JOIN stcoop.invoice i on i.id_set = irs.id
    LEFT JOIN stcoop.invoice_item ii on ii.parent = i.id
    LEFT JOIN stcoop.titulo_movimento tm on tm.id_titulo_movimento = ii.id_title_moviment
    left join stcoop.endereco en on en.cnpj_cpf = cli.cnpj_cpf
WHERE
    -- iss.description <> 'CANCELADO'
    cast(irs.date_cancellation AS date) = date('2025-11-19')
GROUP BY
    CASE
        WHEN cata.nome LIKE '%FTR%' THEN cata.nome
        ELSE cata.fantasia
    END

UNION ALL

SELECT
    CASE
        WHEN cata.nome LIKE '%FTR%' THEN cata.nome
        ELSE cata.fantasia
    END AS unidade,
    COUNT(DISTINCT coalesce(iv.board, it.board)) AS quantidade_placas,
    'Viavante' as empresa
FROM viavante.INSURANCE_REGISTRATION ir
    LEFT JOIN viavante.CLIENTE cli ON cli.CODIGO = ir.CUSTOMER_ID
    LEFT JOIN viavante.CATALOGO cat ON cat.CNPJ_CPF = cli.CNPJ_CPF
    LEFT JOIN viavante.INSURANCE_REG_SET irs ON irs.PARENT = ir.ID
    LEFT JOIN viavante.INSURANCE_STATUS iss ON iss.ID = irs.ID_STATUS
    LEFT JOIN viavante.REPRESENTANTE r ON r.CODIGO = irs.ID_UNITY
    LEFT JOIN viavante.CATALOGO cata ON cata.CNPJ_CPF = r.CNPJ_CPF
    LEFT JOIN viavante.VENDEDOR v ON v.CODIGO = irs.ID_CONSULTANT
    LEFT JOIN viavante.INSURANCE_REG_SET_COVERAGE irsc ON irsc.PARENT = irs.ID
    LEFT JOIN viavante.PRICE_LIST_BENEFITS plb ON plb.ID = irsc.ID_PRICE_LIST
    LEFT JOIN viavante.TYPE_CATEGORY tc ON tc.ID = plb.ID_TYPE_CATEGORY
    LEFT JOIN viavante.CATEGORY c ON c.ID = tc.ID_CATEGORY
    LEFT JOIN viavante.BENEFITS b ON b.ID = c.ID_BENEFITS
    LEFT JOIN viavante.INSURANCE_VEHICLE iv ON iv.ID = irsc.ID_VEHICLE
    LEFT JOIN viavante.TIPO_VEICULO tv ON tv.CODIGO = iv.CODE_TYPE_VEHICLE
    LEFT JOIN viavante.INSURANCE_REG_SET_COV_TRAILER irsct ON irsct.PARENT = irsc.ID
    LEFT JOIN viavante.INSURANCE_TRAILER it ON it.ID = irsct.ID_TRAILER
    LEFT JOIN viavante.MARCA_VEICULO ma ON ma.CODIGO = iv.CODE_BRAND_VEHICLE
    LEFT JOIN viavante.invoice i on i.id_set = irs.id
    LEFT JOIN viavante.invoice_item ii on ii.parent = i.id
    LEFT JOIN viavante.titulo_movimento tm on tm.id_titulo_movimento = ii.id_title_moviment
    left join viavante.endereco en on en.cnpj_cpf = cli.cnpj_cpf
WHERE
    -- iss.description <> 'CANCELADO'
    cast(irs.date_cancellation AS date) = date('2025-11-19')
GROUP BY
    CASE
        WHEN cata.nome LIKE '%FTR%' THEN cata.nome
        ELSE cata.fantasia
    END
    
UNION ALL
    
SELECT
    CASE
        WHEN cata.nome LIKE '%FTR%' THEN cata.nome
        ELSE cata.fantasia
    END AS unidade,
    COUNT(DISTINCT coalesce(iv.board, it.board)) AS quantidade_placas,
    'Tag' as empresa
FROM tag.INSURANCE_REGISTRATION ir
    LEFT JOIN tag.CLIENTE cli ON cli.CODIGO = ir.CUSTOMER_ID
    LEFT JOIN tag.CATALOGO cat ON cat.CNPJ_CPF = cli.CNPJ_CPF
    LEFT JOIN tag.INSURANCE_REG_SET irs ON irs.PARENT = ir.ID
    LEFT JOIN tag.INSURANCE_STATUS iss ON iss.ID = irs.ID_STATUS
    LEFT JOIN tag.REPRESENTANTE r ON r.CODIGO = irs.ID_UNITY
    LEFT JOIN tag.CATALOGO cata ON cata.CNPJ_CPF = r.CNPJ_CPF
    LEFT JOIN tag.VENDEDOR v ON v.CODIGO = irs.ID_CONSULTANT
    LEFT JOIN tag.INSURANCE_REG_SET_COVERAGE irsc ON irsc.PARENT = irs.ID
    LEFT JOIN tag.PRICE_LIST_BENEFITS plb ON plb.ID = irsc.ID_PRICE_LIST
    LEFT JOIN tag.TYPE_CATEGORY tc ON tc.ID = plb.ID_TYPE_CATEGORY
    LEFT JOIN tag.CATEGORY c ON c.ID = tc.ID_CATEGORY
    LEFT JOIN tag.BENEFITS b ON b.ID = c.ID_BENEFITS
    LEFT JOIN tag.INSURANCE_VEHICLE iv ON iv.ID = irsc.ID_VEHICLE
    LEFT JOIN tag.TIPO_VEICULO tv ON tv.CODIGO = iv.CODE_TYPE_VEHICLE
    LEFT JOIN tag.INSURANCE_REG_SET_COV_TRAILER irsct ON irsct.PARENT = irsc.ID
    LEFT JOIN tag.INSURANCE_TRAILER it ON it.ID = irsct.ID_TRAILER
    LEFT JOIN tag.MARCA_VEICULO ma ON ma.CODIGO = iv.CODE_BRAND_VEHICLE
    LEFT JOIN tag.invoice i on i.id_set = irs.id
    LEFT JOIN tag.invoice_item ii on ii.parent = i.id
    LEFT JOIN tag.titulo_movimento tm on tm.id_titulo_movimento = ii.id_title_moviment
    left join tag.endereco en on en.cnpj_cpf = cli.cnpj_cpf
WHERE
    -- iss.description <> 'CANCELADO'
    cast(irs.date_cancellation AS date) = date('2025-11-19')
GROUP BY
    CASE
        WHEN cata.nome LIKE '%FTR%' THEN cata.nome
        ELSE cata.fantasia
    END
    
ORDER BY unidade,empresa ASC;
