UNION ALL --------------------------------------------------------------

SELECT DISTINCT
    cata.fantasia AS "unidade",
    'tag' AS empresa
FROM tag.insurance_reg_set irs
    LEFT JOIN tag.representante r ON r.codigo = irs.id_unity
    LEFT JOIN tag.catalogo cata ON cata.cnpj_cpf = r.cnpj_cpf
WHERE cata.fantasia LIKE '%TS%'