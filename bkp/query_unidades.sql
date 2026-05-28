SELECT DISTINCT
    UPPER(cata.fantasia) AS "unidade",
    cata.nome AS "nome",
    cata.cnpj_cpf,
    'segtruck' AS empresa
FROM silver.insurance_reg_set irs
    LEFT JOIN silver.representante r ON r.codigo = irs.id_unity
    LEFT JOIN silver.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
WHERE UPPER(cata.nome) LIKE '%DIGITAL%'

UNION ALL --------------------------------------------------------------

SELECT DISTINCT
    UPPER(cata.fantasia) AS "unidade",
    cata.nome AS "nome",
    cata.cnpj_cpf,
    'stcoop' AS empresa
FROM stcoop.insurance_reg_set irs
    LEFT JOIN stcoop.representante r ON r.codigo = irs.id_unity
    LEFT JOIN stcoop.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
WHERE UPPER(cata.nome) LIKE '%DIGITAL%'

UNION ALL --------------------------------------------------------------

SELECT DISTINCT
    UPPER(cata.fantasia) AS "unidade",
    cata.nome AS "nome",
    cata.cnpj_cpf,
    'viavante' AS empresa
FROM viavante.insurance_reg_set irs
    LEFT JOIN viavante.representante r ON r.codigo = irs.id_unity
    LEFT JOIN viavante.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
WHERE UPPER(cata.nome) LIKE '%DIGITAL%'

UNION ALL --------------------------------------------------------------

SELECT DISTINCT
    UPPER(cata.fantasia) AS "unidade",
    cata.nome AS "nome",
    cata.cnpj_cpf,
    'tag' AS empresa
FROM tag.insurance_reg_set irs
    LEFT JOIN tag.representante r ON r.codigo = irs.id_unity
    LEFT JOIN tag.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
WHERE UPPER(cata.nome) LIKE '%DIGITAL%'
