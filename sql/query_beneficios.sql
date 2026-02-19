SELECT DISTINCT
    b.id AS "id_beneficio",
    b.description AS "beneficio",
    'segtruck' AS empresa
FROM silver.price_list_benefits plb
    LEFT JOIN silver.type_category tc ON tc.id = plb.id_type_category
    LEFT JOIN silver.category c ON c.id = tc.id_category
    LEFT JOIN silver.benefits b ON b.id = c.id_benefits
WHERE b.id IN (2, 3, 4, 7, 24, 25, 26, 29)

UNION ALL --------------------------------------------------------------

SELECT DISTINCT
    b.id AS "id_beneficio",
    b.description AS "beneficio",
    'stcoop' AS empresa
FROM stcoop.price_list_benefits plb
    LEFT JOIN stcoop.type_category tc ON tc.id = plb.id_type_category
    LEFT JOIN stcoop.category c ON c.id = tc.id_category
    LEFT JOIN stcoop.benefits b ON b.id = c.id_benefits
WHERE b.id IN (24, 25, 26, 29)

UNION ALL --------------------------------------------------------------

SELECT DISTINCT
    b.id AS "id_beneficio",
    b.description AS "beneficio",
    'viavante' AS empresa
FROM viavante.price_list_benefits plb
    LEFT JOIN viavante.type_category tc ON tc.id = plb.id_type_category
    LEFT JOIN viavante.category c ON c.id = tc.id_category
    LEFT JOIN viavante.benefits b ON b.id = c.id_benefits
WHERE b.id IN (40, 41, 42, 45)

UNION ALL --------------------------------------------------------------

SELECT DISTINCT
    b.id AS "id_beneficio",
    b.description AS "beneficio",
    'tag' AS empresa
FROM tag.price_list_benefits plb
    LEFT JOIN tag.type_category tc ON tc.id = plb.id_type_category
    LEFT JOIN tag.category c ON c.id = tc.id_category
    LEFT JOIN tag.benefits b ON b.id = c.id_benefits
WHERE b.id IN (2, 3, 4, 7, 24, 25, 26, 29, 34, 35, 36, 37, 38, 39)
