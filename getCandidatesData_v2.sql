--SCRIPT DE TRAITEMENT: RECHERCHE DE CORRESPONDANCES VALABLES DANS LES ANNUAIRES
---------------------------------------------------------------------------------
---------------------------------------------------------------------------------
--CREATION DE QUELQUES INDEX POUR ACCELERER LE SCRIPT
-- 1. Activer l'extension de recherche textuelle floue (si ce n'est pas déjà fait)
-- 1. On crée notre propre fonction unaccent marquée comme IMMUTABLE
CREATE OR REPLACE FUNCTION testing.f_unaccent(text)
  RETURNS text AS
$$
  SELECT public.unaccent($1);
$$
LANGUAGE sql IMMUTABLE
PARALLEL SAFE;

-- L'index pour le NOM (per)
CREATE INDEX IF NOT EXISTS idx_all_data_per_trgm 
ON testing.all_data USING gin (LOWER(testing.f_unaccent(per)) gin_trgm_ops);

-- L'index pour l'ACTIVITÉ (act)
CREATE INDEX IF NOT EXISTS idx_all_data_act_trgm 
ON testing.all_data USING gin (LOWER(testing.f_unaccent(act)) gin_trgm_ops);
-------------------------------------------------------------
--pre: creer table des resultats

--version dessinateur
DROP TABLE IF EXISTS testing.candidates_artist;

CREATE TABLE IF NOT EXISTS testing.candidates_artist (
    uri_agent CHARACTER VARYING,
    uuid CHARACTER VARYING,
	per CHARACTER VARYING,
    act CHARACTER VARYING, 
    pub_year BIGINT,
	beginning_year_calc BIGINT,
	end_year_calc BIGINT,
    book CHARACTER VARYING, 
    collection CHARACTER VARYING,
    addr_num CHARACTER VARYING, 
    addr_name CHARACTER VARYING, 
    geo_source CHARACTER VARYING, 
	view_link CHARACTER VARYING,
    geom GEOMETRY(Point, 4326),
    surname_searched CHARACTER VARYING,
	first_name_searched CHARACTER VARYING
    );
------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_candidates_artist_per ON testing.candidates_artist (per);
CREATE INDEX IF NOT EXISTS idx_candidates_artist_act ON testing.candidates_artist (act);
CREATE INDEX IF NOT EXISTS idx_candidates_artist_pub_year ON testing.candidates_artist (pub_year);
CREATE INDEX IF NOT EXISTS idx_candidates_artist_surname_searched ON testing.candidates_artist (surname_searched);
CREATE INDEX IF NOT EXISTS idx_candidates_artist_first_name_searched ON testing.candidates_artist (first_name_searched);
-- Index spatial pour que le clustering (Étape B) soit instantané
CREATE INDEX IF NOT EXISTS idx_candidates_artist_geom ON testing.candidates_artist USING GIST (geom);
---------------------------------------------------------------------------------
--version imprimeur
DROP TABLE IF EXISTS testing.candidates_printer;

CREATE TABLE IF NOT EXISTS testing.candidates_printer (
    uri_agent CHARACTER VARYING,
    uuid CHARACTER VARYING,
	per CHARACTER VARYING,
    act CHARACTER VARYING, 
    pub_year BIGINT,
	beginning_year_calc BIGINT,
	end_year_calc BIGINT,
    book CHARACTER VARYING, 
    collection CHARACTER VARYING,
    addr_num CHARACTER VARYING, 
    addr_name CHARACTER VARYING, 
    geo_source CHARACTER VARYING, 
	view_link CHARACTER VARYING,
    geom GEOMETRY(Point, 4326),
    surname_searched CHARACTER VARYING,
	first_name_searched CHARACTER VARYING
    );
------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_candidates_printer_per ON testing.candidates_printer (per);
CREATE INDEX IF NOT EXISTS idx_candidates_printer_act ON testing.candidates_printer (act);
CREATE INDEX IF NOT EXISTS idx_candidates_printer_pub_year ON testing.candidates_printer (pub_year);
CREATE INDEX IF NOT EXISTS idx_candidates_printer_surname_searched ON testing.candidates_printer (surname_searched);
CREATE INDEX IF NOT EXISTS idx_candidates_printer_first_name_searched ON testing.candidates_printer (first_name_searched);
-- Index spatial pour que le clustering (Étape B) soit instantané
CREATE INDEX IF NOT EXISTS idx_candidates_printer_geom ON testing.candidates_printer USING GIST (geom);
--------------------------------------------------------------------------------
--Que fait cette fonction?
--a)Filtre sur les colonnes debut et fin: condition, recupérer les entrees qui correspondent à l'intervalle puis,
--poser la condition que si int<10 on fait : x=round((10-int)/2) et on modifie la recherche pour avoir 
--a gauche  et a droite 10-int-x
--c)filtre sur le surname (dynamique)

--version dessinateur
DROP FUNCTION IF EXISTS testing.getCandidatesData_artist;

CREATE OR REPLACE FUNCTION testing.getCandidatesData_artist (
uri CHARACTER VARYING,
surname CHARACTER VARYING,
first_name CHARACTER VARYING DEFAULT '',
debut BIGINT DEFAULT 1800,
fin BIGINT DEFAULT 1950
)

RETURNS TABLE(
	uri_agent CHARACTER VARYING,
    uuid CHARACTER VARYING,
	per CHARACTER VARYING,
    act CHARACTER VARYING, 
    pub_year BIGINT,
	beginning_year_calc_out BIGINT,
	end_year_calc_out BIGINT,
    book CHARACTER VARYING, 
    collection CHARACTER VARYING,
    addr_num CHARACTER VARYING, 
    addr_name CHARACTER VARYING, 
    geo_source CHARACTER VARYING,
	view_link CHARACTER VARYING,
    geom GEOMETRY(Point, 4326),
    surname_searched CHARACTER VARYING,
	first_name_searched CHARACTER VARYING

)

AS $$
DECLARE
	intervalle INTEGER;
	x INTEGER;
	beginning_year_calc BIGINT;
	end_year_calc BIGINT;
	intervalle_calc BIGINT;
BEGIN
	intervalle := fin-debut;
	IF 
		intervalle<10 THEN
		x := ROUND((10-intervalle)/2);
		beginning_year_calc := debut-x;
		end_year_calc := fin+(10-intervalle-x);
	ELSE 
		beginning_year_calc := debut;
		end_year_calc := fin;
	END IF;
	
	RETURN QUERY
	SELECT
	uri,
    ad.uuid,
	ad.per,
	ad.act,
	ad."source.publication_year",
	beginning_year_calc,
	end_year_calc,
	ad."source.book",
	ad."source.collection",
	ad."address.number", essayant de relever tous les cas possibles de “formats” de noms ou raisons sociales: 
	ad."address.name",
	ad."geocoding.response.source",
	ad."source.view_link",
	ad.geom,
	surname,
	first_name
	
FROM testing.all_data ad
WHERE 
	ad."source.publication_year" BETWEEN beginning_year_calc AND end_year_calc
AND
	unaccent(ad.per) ILIKE ('%'||surname||'%')
AND (unaccent(ad.act) ~* 'dessin|artiste|peintre|affich');

END;
$$ LANGUAGE plpgsql;
---------------------------------------------------------------------------------------------------------------
--version imprimeur
DROP FUNCTION IF EXISTS testing.getCandidatesData_printer;

CREATE OR REPLACE FUNCTION testing.getCandidatesData_printer (
uri CHARACTER VARYING,
surname CHARACTER VARYING,
first_name CHARACTER VARYING DEFAULT '',
debut BIGINT DEFAULT 1800,
fin BIGINT DEFAULT 1950
)

RETURNS TABLE(
    uri_agent CHARACTER VARYING,
	uuid CHARACTER VARYING,
	per CHARACTER VARYING,
    act CHARACTER VARYING, 
    pub_year BIGINT,
	beginning_year_calc_out BIGINT,
	end_year_calc_out BIGINT,
    book CHARACTER VARYING, 
    collection CHARACTER VARYING,
    addr_num CHARACTER VARYING, 
    addr_name CHARACTER VARYING, 
    geo_source CHARACTER VARYING,
	view_link CHARACTER VARYING,
    geom GEOMETRY(Point, 4326),
    surname_searched CHARACTER VARYING,
	first_name_searched CHARACTER VARYING
)

AS $$
DECLARE
	intervalle INTEGER;
	x INTEGER;
	beginning_year_calc BIGINT;
	end_year_calc BIGINT;
	intervalle_calc BIGINT;
BEGIN
	intervalle := fin-debut;
	IF 
		intervalle<10 THEN
		x := ROUND((10-intervalle)/2);
		beginning_year_calc := debut-x;
		end_year_calc := fin+(10-intervalle-x);
	ELSE 
		beginning_year_calc := debut;
		end_year_calc := fin;
	END IF;
	
	RETURN QUERY
	SELECT
    uri,
	ad.uuid,
	ad.per,
	ad.act,
	ad."source.publication_year",
	beginning_year_calc,
	end_year_calc,
	ad."source.book",
	ad."source.collection",
	ad."address.number",
	ad."address.name",
	ad."geocoding.response.source",
	ad."source.view_link",
	ad.geom,
	surname,
	first_name
	
FROM testing.all_data ad
WHERE 
	ad."source.publication_year" BETWEEN beginning_year_calc AND end_year_calc
AND
	unaccent(ad.per) ILIKE ('%'||surname||'%')
AND (unaccent(ad.act) ~* 'impr|lithogr|libr|bibli|grav|dominot|press|typo');

END;
$$ LANGUAGE plpgsql;
--------------------------------------------------------------------------------------------
--------------------------------------------------------------------------------------------
--GET DATA AND SPATIAL CLUSTERING FUNCTION
--pre: creer table des resultats

--version dessinateur
DROP TABLE IF EXISTS testing.candidates_spatial_cluster_points_artist;

CREATE TABLE IF NOT EXISTS testing.candidates_spatial_cluster_points_artist (
    uri_agent CHARACTER VARYING,
    uuid CHARACTER VARYING,
	cluster_id INTEGER,
   	per CHARACTER VARYING,
	jarowinkler_per NUMERIC,
    act CHARACTER VARYING,
	jarowinkler_act NUMERIC,
    pub_year BIGINT,
	beginning_year_calc BIGINT,
	end_year_calc BIGINT,
    directory CHARACTER VARYING, 
    collection CHARACTER VARYING,
    addr_num CHARACTER VARYING, 
    addr_name CHARACTER VARYING,
    address CHARACTER VARYING, 
    geo_source CHARACTER VARYING, 
	view_link CHARACTER VARYING,
    geom GEOMETRY(Point, 4326),
    surname_searched CHARACTER VARYING,
	first_name_searched CHARACTER VARYING
	);

CREATE INDEX IF NOT EXISTS idx_candidates_artist_cluster_geom ON testing.candidates_spatial_cluster_points_artist USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_candidates_artist_cluster_cluster_id ON testing.candidates_spatial_cluster_points_artist (cluster_id);
-----------------------------------------------------------------------------
--version imprimeur
DROP TABLE IF EXISTS testing.candidates_spatial_cluster_points_printer;

CREATE TABLE IF NOT EXISTS testing.candidates_spatial_cluster_points_printer (
    uri_agent CHARACTER VARYING,
    uuid CHARACTER VARYING,
	cluster_id INTEGER,
   	per CHARACTER VARYING,
	jarowinkler_per NUMERIC,
    act CHARACTER VARYING,
	jarowinkler_act NUMERIC,
    pub_year BIGINT,
	beginning_year_calc BIGINT,
	end_year_calc BIGINT,
    directory CHARACTER VARYING, 
    collection CHARACTER VARYING,
    addr_num CHARACTER VARYING, 
    addr_name CHARACTER VARYING,
    address CHARACTER VARYING, 
    geo_source CHARACTER VARYING, 
	view_link CHARACTER VARYING,
    geom GEOMETRY(Point, 4326),
    surname_searched CHARACTER VARYING,
	first_name_searched CHARACTER VARYING
	);

CREATE INDEX IF NOT EXISTS idx_candidates_printer_cluster_geom ON testing.candidates_spatial_cluster_points_printer USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_candidates_printer_cluster_cluster_id ON testing.candidates_spatial_cluster_points_printer (cluster_id);
------------------------------------------------------------
--Que fait cette fonction?
--elle va chercher dans la table des candidats computee precedemment, les candidats assimilables 
--a un cluster en se basant seulement sur la posituion de ceux ci

--version dessinateur
DROP FUNCTION IF EXISTS testing.get_candidates_data_spatial_cluster_artist;

CREATE OR REPLACE FUNCTION testing.get_candidates_data_spatial_cluster_artist(
    surname CHARACTER VARYING,
    first_name CHARACTER VARYING DEFAULT NULL
	)
RETURNS TABLE (
    uri_agent CHARACTER VARYING,
    uuid CHARACTER VARYING,
    cluster_id INTEGER,
    per CHARACTER VARYING,
    jarowinkler_per NUMERIC,
	act CHARACTER VARYING,
	jarowinkler_act NUMERIC,
    pub_year BIGINT, 
	beginning_year_calc BIGINT,
	end_year_calc BIGINT,
    directory CHARACTER VARYING, 
    collection CHARACTER VARYING,
    addr_num CHARACTER VARYING,
    addr_name CHARACTER VARYING,
    address CHARACTER VARYING,
    geo_source CHARACTER VARYING,
	view_link CHARACTER VARYING,
    geom GEOMETRY(Point, 4326),
	surname_searched CHARACTER VARYING,
	first_name_searched CHARACTER VARYING
) 
AS $$
DECLARE 
		v_first_name TEXT := COALESCE(first_name, '');
BEGIN
    RETURN QUERY
    SELECT 
        ca.uri_agent,
        ca.uuid,
        -- 1. Clustering spatial (EPS 50m)
        ST_ClusterDBSCAN(ST_Transform(ca.geom, 2154), eps := 50, minpoints := 2) OVER()::INTEGER AS cluster_id,
        ca.per,
        -- 2. Calcul du meilleur score JW (Argmax)
        GREATEST(
            jarowinkler(testing.normalize_per(ca.per), testing.normalize_per(surname)),
			CASE
				WHEN v_first_name <> '' THEN
            		jarowinkler(testing.normalize_per(ca.per), testing.normalize_per(surname || ' ' || v_first_name))
				ELSE 0
			END
        )::NUMERIC AS jarowinkler_per,
        ca.act,
		-- Score Métier unique (Meilleur score parmi tous les mots-clés)
        GREATEST(
            jarowinkler(unaccent(ca.act), 'peintre'), jarowinkler(unaccent(ca.act), 'artiste'),
			jarowinkler(unaccent(ca.act), 'peintre-artiste'), jarowinkler(unaccent(ca.act), 'artiste-peintre'),
            jarowinkler(unaccent(ca.act), 'architecte'), jarowinkler(unaccent(ca.act), 'dessinateur'),
            jarowinkler(unaccent(ca.act), 'affiche'), jarowinkler(unaccent(ca.act), 'imprimerie'), 
            jarowinkler(unaccent(ca.act), 'typographe'), jarowinkler(unaccent(ca.act), 'lithographe'), 
            jarowinkler(unaccent(ca.act), 'graveur'), jarowinkler(unaccent(ca.act), 'imprimeur'),
			jarowinkler(unaccent(ca.act), 'imprimeur-lithographe'), jarowinkler(unaccent(ca.act), 'imprimeur-typographe')
        )::NUMERIC AS jarowinkler_act,
        ca.pub_year, 
		ca.beginning_year_calc,
		ca.end_year_calc,
        ca.book as directory,
        ca.collection,
        ca.addr_num,
        ca.addr_name,
        trim(concat_ws(' ',ca.addr_num, ca.addr_name))::CHARACTER VARYING as address,
        ca.geo_source,
		ca.view_link,
        ca.geom,
		ca.surname_searched,
		ca.first_name_searched
    FROM testing.candidates_artist ca
    WHERE ca.surname_searched = surname;
END;
$$ LANGUAGE plpgsql;
---------------------------------------------------------------------------------
--version imprimeur
DROP FUNCTION IF EXISTS testing.get_candidates_data_spatial_cluster_printer;

CREATE OR REPLACE FUNCTION testing.get_candidates_data_spatial_cluster_printer(
    surname CHARACTER VARYING,
    first_name CHARACTER VARYING DEFAULT NULL
	)
RETURNS TABLE (
    uri_agent CHARACTER VARYING,
    uuid CHARACTER VARYING,
    cluster_id INTEGER,
    per CHARACTER VARYING,
    jarowinkler_per NUMERIC,
	act CHARACTER VARYING,
	jarowinkler_act NUMERIC,
    pub_year BIGINT, 
	beginning_year_calc BIGINT,
	end_year_calc BIGINT,
    directory CHARACTER VARYING, 
    collection CHARACTER VARYING,
    addr_num CHARACTER VARYING,
    addr_name CHARACTER VARYING,
    address CHARACTER VARYING,
    geo_source CHARACTER VARYING,
	view_link CHARACTER VARYING,
    geom GEOMETRY(Point, 4326),
	surname_searched CHARACTER VARYING,
	first_name_searched CHARACTER VARYING
) 
AS $$
DECLARE 
		v_first_name TEXT := COALESCE(first_name, '');
BEGIN
    RETURN QUERY
    SELECT 
        cp.uri_agent,
        cp.uuid,
        -- 1. Clustering spatial (EPS 50m)
        ST_ClusterDBSCAN(ST_Transform(cp.geom, 2154), eps := 50, minpoints := 2) OVER()::INTEGER AS cluster_id,
        cp.per,
        -- 2. Calcul du meilleur score JW (Argmax)
        GREATEST(
            jarowinkler(testing.normalize_per(cp.per), testing.normalize_per(surname)),
			CASE
				WHEN v_first_name <> '' THEN
            		jarowinkler(testing.normalize_per(cp.per), testing.normalize_per(surname || ' ' || v_first_name))
				ELSE 0
			END
        )::NUMERIC AS jarowinkler_per,
        cp.act,
		-- Score Métier unique (Meilleur score parmi tous les mots-clés)
        GREATEST(
            jarowinkler(unaccent(cp.act), 'peintre'), jarowinkler(unaccent(cp.act), 'artiste'),
			jarowinkler(unaccent(cp.act), 'peintre-artiste'), jarowinkler(unaccent(cp.act), 'artiste-peintre'),
            jarowinkler(unaccent(cp.act), 'architecte'), jarowinkler(unaccent(cp.act), 'dessinateur'),
            jarowinkler(unaccent(cp.act), 'affiche'), jarowinkler(unaccent(cp.act), 'imprimerie'), 
            jarowinkler(unaccent(cp.act), 'typographe'), jarowinkler(unaccent(cp.act), 'lithographe'), 
            jarowinkler(unaccent(cp.act), 'graveur'), jarowinkler(unaccent(cp.act), 'imprimeur'),
			jarowinkler(unaccent(cp.act), 'imprimeur-lithographe'), jarowinkler(unaccent(cp.act), 'imprimeur-typographe')
        )::NUMERIC AS jarowinkler_act,
        cp.pub_year, 
		cp.beginning_year_calc,
		cp.end_year_calc,
        cp.book as directory,
        cp.collection,
        cp.addr_num,
        cp.addr_name,
		trim(concat_ws(' ',cp.addr_num, cp.addr_name))::CHARACTER VARYING as address,
        cp.geo_source,
		cp.view_link,
        cp.geom,
		cp.surname_searched,
		cp.first_name_searched
        
    FROM testing.candidates_printer cp
    WHERE cp.surname_searched = surname;
END;
$$ LANGUAGE plpgsql;
--------------------------------------------------------------------------------
--------------------------------------------------------------------------------
--THIS FUNCTION SUMMARIZES THE SPATIAL DATA CLUSTERING RESULT

--version dessinateur
DROP FUNCTION IF EXISTS testing.get_candidates_clusters_artist;

CREATE OR REPLACE FUNCTION testing.get_candidates_clusters_artist()
RETURNS VOID AS $$
BEGIN
	CREATE INDEX IF NOT EXISTS idx_spatial_points_artist_composite 
    ON testing.candidates_spatial_cluster_points_artist (uri_agent, surname_searched, first_name_searched, cluster_id);
    DROP TABLE IF EXISTS testing.candidates_clusters_artist;

    CREATE TABLE testing.candidates_clusters_artist AS
    WITH cluster_stats AS (
        SELECT 
            uri_agent,
            surname_searched,
            first_name_searched,
            cluster_id,
            string_agg(DISTINCT per, ' | ') AS directory_names,
            string_agg(DISTINCT act, ' | ') AS activities,
            MIN(pub_year) AS beginning_year,
            MAX(pub_year) AS end_year,
            COUNT(*) AS nb_points,
            ROUND(AVG(jarowinkler_per), 3) AS jw_per_avg,
            ROUND(AVG(jarowinkler_act), 3) AS jw_act_avg,
            ROUND(
                COUNT(*)::NUMERIC / 
                NULLIF((MAX(pub_year) - MIN(pub_year) + 1), 0), 2
            ) AS time_density,
            ST_Collect(geom)::GEOMETRY(MultiPoint, 4326) AS cluster_geometry
        FROM testing.candidates_spatial_cluster_points_artist
        WHERE cluster_id IS NOT NULL 
        GROUP BY uri_agent, surname_searched, first_name_searched, cluster_id
    ),
    frequent_triplet AS (
        SELECT DISTINCT ON (uri_agent, surname_searched, first_name_searched, cluster_id)
            uri_agent, surname_searched, first_name_searched, cluster_id,
            per as per_cluster,
            act as act_cluster,
            addr_name as addr_name_cluster,
            addr_num as addr_num_cluster,
            geom as address_geometry, -- surnamemé ici
            COUNT(*) OVER(PARTITION BY uri_agent, surname_searched, first_name_searched, cluster_id, per, act, addr_name, addr_num, geom) as freq
        FROM testing.candidates_spatial_cluster_points_artist
        WHERE cluster_id IS NOT NULL
        ORDER BY uri_agent, surname_searched, first_name_searched, cluster_id, freq DESC
    )
    SELECT 
        gen_random_uuid() as uuid_cluster,
        cs.*,
        ft.per_cluster,
        ft.act_cluster,
        ft.addr_name_cluster,
        ft.addr_num_cluster,
        trim(concat_ws(' ',ft.addr_num_cluster, ft.addr_name_cluster)) as address_cluster,
        ft.address_geometry -- Corrigé pour correspondre à la CTE
    FROM cluster_stats cs
    JOIN frequent_triplet ft ON 
        cs.uri_agent = ft.uri_agent AND 
        cs.surname_searched = ft.surname_searched AND 
        cs.first_name_searched = ft.first_name_searched AND
        cs.cluster_id = ft.cluster_id;

    CREATE INDEX idx_clusters_multipoint_artist_geom ON testing.candidates_clusters_artist USING GIST (cluster_geometry);
    CREATE INDEX idx_clusters_multipoint_artist_jw ON testing.candidates_clusters_artist (jw_act_avg, jw_per_avg);
    RAISE NOTICE 'Table testing.candidates_clusters_artist créée avec succès.';
END;
$$ LANGUAGE plpgsql;
---------------------------------------------------
--version imprimeur
DROP FUNCTION IF EXISTS testing.get_candidates_clusters_printer;

CREATE OR REPLACE FUNCTION testing.get_candidates_clusters_printer()
RETURNS VOID AS $$
BEGIN
	CREATE INDEX IF NOT EXISTS idx_spatial_points_printer_composite 
    ON testing.candidates_spatial_cluster_points_printer (uri_agent, surname_searched, first_name_searched, cluster_id);
    DROP TABLE IF EXISTS testing.candidates_clusters_printer;

    CREATE TABLE testing.candidates_clusters_printer AS
    WITH cluster_stats AS (
        -- Étape 1 : Calcul des statistiques globales par cluster
        SELECT 
            uri_agent,
            surname_searched,
            first_name_searched,
            cluster_id,
            string_agg(DISTINCT per, ' | ') AS directory_names,
            string_agg(DISTINCT act, ' | ') AS activities,
            MIN(pub_year) AS beginning_year,
            MAX(pub_year) AS end_year,
            COUNT(*) AS nb_points,
            ROUND(AVG(jarowinkler_per), 3) AS jw_per_avg,
            ROUND(AVG(jarowinkler_act), 3) AS jw_act_avg,
            ROUND(
                COUNT(*)::NUMERIC / 
                NULLIF((MAX(pub_year) - MIN(pub_year) + 1), 0), 2
            ) AS time_density,
            ST_Collect(geom)::GEOMETRY(MultiPoint, 4326) AS cluster_geometry
        FROM testing.candidates_spatial_cluster_points_printer
        WHERE cluster_id IS NOT NULL 
        GROUP BY uri_agent, surname_searched, first_name_searched, cluster_id
    ),
    frequent_triplet AS (
        -- Étape 2 : Sélection du triplet (surname, act, rue, num, geom) le plus fréquent
        SELECT DISTINCT ON (uri_agent, surname_searched, first_name_searched, cluster_id)
            uri_agent, surname_searched, first_name_searched, cluster_id,
            per as per_cluster,
            act as act_cluster,
            addr_name as addr_name_cluster,
            addr_num as addr_num_cluster,
            geom as address_geometry,
            COUNT(*) OVER(PARTITION BY uri_agent, surname_searched, first_name_searched, cluster_id, per, act, addr_name, addr_num, geom) as freq
        FROM testing.candidates_spatial_cluster_points_printer
        WHERE cluster_id IS NOT NULL
        ORDER BY uri_agent, surname_searched, first_name_searched, cluster_id, freq DESC
    )
    -- Étape 3 : Assemblage final avec la colonne d'adresse concaténée
    SELECT 
        gen_random_uuid() as uuid_cluster,
        cs.*,
        ft.per_cluster,
        ft.act_cluster,
        ft.addr_name_cluster,
        ft.addr_num_cluster,
        trim(concat_ws(' ', ft.addr_num_cluster, ft.addr_name_cluster)) as address_cluster,
        ft.address_geometry
    FROM cluster_stats cs
    JOIN frequent_triplet ft ON 
        cs.uri_agent = ft.uri_agent AND 
        cs.surname_searched = ft.surname_searched AND 
        cs.first_name_searched = ft.first_name_searched AND
        cs.cluster_id = ft.cluster_id;

    -- Indexation spatiale pour les performances SIG
    CREATE INDEX idx_clusters_multipoint_printer_geom ON testing.candidates_clusters_printer USING GIST (cluster_geometry);
	CREATE INDEX idx_clusters_multipoint_printer_jw ON testing.candidates_clusters_printer (jw_act_avg, jw_per_avg);
    
    RAISE NOTICE 'Table testing.candidates_clusters_printer créée avec succès.';
END;
$$ LANGUAGE plpgsql;
-----------------------------------------------------------------------------------------------
-----------------------------------------------------------------------------------------------
--CREATES A TABLE TO STORE CANDIDATES THAT HAVE BEEN REJECTED, NOT REALLY PROBABLE, OR PROBABLE
--ENSUITE LES PROBABLES ET PEU PROBAABLES FAIRE UN RANKING DESSSU EN SE BASANT SUR LA CATEGORIE, LE S_JW ET ENFIN LA DENSITE

--version dessinateur
DROP FUNCTION IF EXISTS testing.classify_candidates_artist;

CREATE OR REPLACE FUNCTION testing.classify_candidates_artist()
RETURNS VOID AS $$
BEGIN
    
    DROP TABLE IF EXISTS testing.likely_candidates_artist;
--table poyur candidats probables
    CREATE TABLE testing.likely_candidates_artist AS
    SELECT *
    FROM testing.candidates_clusters_artist
	--seuils empiriques
    WHERE jw_per_avg >=0.6
	AND jw_act_avg >=0.6;
    CREATE INDEX idx_likely_candidates_artist_geom ON testing.likely_candidates_artist USING GIST (cluster_geometry);
    RAISE NOTICE 'Table testing.likely_candidates créée avec succès.';
---------------------
--------------------
	DROP TABLE IF EXISTS testing.unlikely_candidates_artist;
--table pour candidates peu probables
    CREATE TABLE testing.unlikely_candidates_artist AS
    SELECT *
    FROM testing.candidates_clusters_artist
	--seuils empiriques
    WHERE jw_per_avg >= 0.6
	AND jw_act_avg < 0.6;
    CREATE INDEX idx_unlikely_candidates_artist_geom ON testing.unlikely_candidates_artist USING GIST (cluster_geometry);
    RAISE NOTICE 'Table testing.unlikely_candidates créée avec succès.';
---------------------
--------------------
	DROP TABLE IF EXISTS testing.improbable_candidates_artist;
--table pour candidates improbables
    CREATE TABLE testing.improbable_candidates_artist AS
    SELECT *
    FROM testing.candidates_clusters_artist
	--seuils empiriques
    WHERE jw_per_avg < 0.6;
	CREATE INDEX idx_improbable_candidates_artist_geom ON testing.improbable_candidates_artist USING GIST (cluster_geometry);
    RAISE NOTICE 'Table testing.improbable_candidates_artist créée avec succès.';
	
END;
$$ LANGUAGE plpgsql;
-----------------------------------------
--version imprimeur
DROP FUNCTION IF EXISTS testing.classify_candidates_printer;

CREATE OR REPLACE FUNCTION testing.classify_candidates_printer()
RETURNS VOID AS $$
BEGIN
    
    DROP TABLE IF EXISTS testing.likely_candidates_printer;
--table poyur candidats probables
    CREATE TABLE testing.likely_candidates_printer AS
    SELECT *
    FROM testing.candidates_clusters_printer
	--seuils empiriques
    WHERE jw_per_avg >=0.6
	AND jw_act_avg >=0.6;
    CREATE INDEX idx_likely_candidates_printer_geom ON testing.likely_candidates_printer USING GIST (cluster_geometry);
    RAISE NOTICE 'Table testing.likely_candidates_printer créée avec succès.';
---------------------
--------------------
	DROP TABLE IF EXISTS testing.unlikely_candidates_printer;
--table pour candidates peu probables
    CREATE TABLE testing.unlikely_candidates_printer AS
    SELECT *
    FROM testing.candidates_clusters_printer
	--seuils empiriques
    WHERE jw_per_avg >= 0.6
	AND jw_act_avg < 0.6;
    CREATE INDEX idx_unlikely_candidates_printer_geom ON testing.unlikely_candidates_printer USING GIST (cluster_geometry);
    RAISE NOTICE 'Table testing.unlikely_candidates_printer créée avec succès.';
---------------------
--------------------
	DROP TABLE IF EXISTS testing.improbable_candidates_printer;
--table pour candidates improbables
    CREATE TABLE testing.improbable_candidates_printer AS
    SELECT *
    FROM testing.candidates_clusters_printer
	--seuils empiriques
    WHERE jw_per_avg < 0.6;
	CREATE INDEX idx_improbable_candidates_printer_geom ON testing.improbable_candidates_printer USING GIST (cluster_geometry);
    RAISE NOTICE 'Table testing.improbable_candidates_printer créée avec succès.';
	
END;
$$ LANGUAGE plpgsql;
------------------------------
--------------------------------
--RANKING FUNCION

--version dessinateur
DROP FUNCTION IF EXISTS testing.rank_candidates_artist;

CREATE OR REPLACE FUNCTION testing.rank_candidates_artist()
RETURNS VOID AS $$
BEGIN
    DROP TABLE IF EXISTS testing.ranked_candidates_artist;

    CREATE TABLE testing.ranked_candidates_artist AS
    SELECT 
        *,
        CASE 
            WHEN jw_per_avg >= 0.6 AND jw_act_avg >= 0.6 THEN 'likely'
            WHEN jw_per_avg >= 0.6 AND jw_act_avg < 0.6  THEN 'unlikely'
            ELSE 'improbable'
        END AS cluster_type,
            RANK() OVER (
            PARTITION BY surname_searched
            ORDER BY jw_per_avg DESC, jw_act_avg DESC, time_density  DESC
        ) AS cluster_rank
    FROM testing.candidates_clusters_artist;

    CREATE INDEX idx_ranked_candidates_artist_surname ON testing.ranked_candidates_artist (surname_searched);
    RAISE NOTICE 'Table testing.ranked_candidates_artist créée avec succès.';
END;
$$ LANGUAGE plpgsql;
-----------------------------
--version imprimeur
DROP FUNCTION IF EXISTS testing.rank_candidates_printer;

CREATE OR REPLACE FUNCTION testing.rank_candidates_printer()
RETURNS VOID AS $$
BEGIN
    DROP TABLE IF EXISTS testing.ranked_candidates_printer;

    CREATE TABLE testing.ranked_candidates_printer AS
    SELECT 
        *,
        CASE 
            WHEN jw_per_avg >= 0.6 AND jw_act_avg >= 0.6 THEN 'likely'
            WHEN jw_per_avg >= 0.6 AND jw_act_avg < 0.6  THEN 'unlikely'
            ELSE 'improbable'
        END AS cluster_type,
            RANK() OVER (
            PARTITION BY surname_searched
            ORDER BY jw_per_avg DESC, jw_act_avg DESC, time_density DESC
        ) AS cluster_rank
    FROM testing.candidates_clusters_printer;

    CREATE INDEX idx_ranked_candidates_printer_surname ON testing.ranked_candidates_printer (surname_searched);
    RAISE NOTICE 'Table testing.ranked_candidates créée avec succès.';
END;
$$ LANGUAGE plpgsql;
------------------------------------------------------------------
------------------------------------------------------------------
--THIS FUNCTION CREATES A TABLE WITH POINTS WITH INFOS ABOUT THEIR CLUSTERS, RANK AND ID
--version dessinateur
DROP FUNCTION IF EXISTS testing.create_points_table_artist;

CREATE OR REPLACE FUNCTION testing.create_points_table_artist()
RETURNS VOID AS $$
BEGIN
DROP TABLE IF EXISTS testing.points_table_artist;
CREATE TABLE testing.points_table_artist AS
SELECT 
    a.uri_agent,
    a.uuid,
    a.cluster_id,
    a.per,
    a.jarowinkler_per,
    a.act,
    a.jarowinkler_act,
    a.pub_year,
    a.beginning_year_calc,
    a.end_year_calc,
    a.directory,
    a.collection,
    a.addr_num,
    a.addr_name,
    a.address,
    a.geo_source,
    a.view_link,
    a.geom,
    a.surname_searched,
    a.first_name_searched,
    r.uuid_cluster,
    r.directory_names,
    r.activities,
    r.beginning_year,
    r.end_year,
    r.nb_points,
    r.jw_per_avg,
    r.jw_act_avg,
    r.time_density,
    r.cluster_geometry,
    r.per_cluster,
    r.act_cluster,
    r.addr_name_cluster,
    r.addr_num_cluster,
    r.address_cluster,
    r.address_geometry,
    r.cluster_type,
    r.cluster_rank
FROM testing.candidates_spatial_cluster_points_artist a
JOIN testing.ranked_candidates_artist r 
  ON a.surname_searched = r.surname_searched 
  -- Ici on s'assure que le point appartient bien à la géométrie du cluster
  AND ST_Intersects(a.geom, r.cluster_geometry);
CREATE INDEX idx_points_table_artist ON testing.points_table_artist USING GIST (geom);
  END;
$$ LANGUAGE plpgsql;


 --version imprimeur
 DROP FUNCTION IF EXISTS testing.create_points_table_printer;

CREATE OR REPLACE FUNCTION testing.create_points_table_printer()
RETURNS VOID AS $$
BEGIN
DROP TABLE IF EXISTS testing.points_table_printer;
CREATE TABLE testing.points_table_printer AS
SELECT 
    p.uri_agent,
    p.uuid,
    p.cluster_id,
    p.per,
    p.jarowinkler_per,
    p.act,
    p.jarowinkler_act,
    p.pub_year,
    p.beginning_year_calc,
    p.end_year_calc,
    p.directory,
    p.collection,
    p.addr_num,
    p.addr_name,
    p.address,
    p.geo_source,
    p.view_link,
    p.geom,
    p.surname_searched,
    p.first_name_searched,
    r.uuid_cluster,
    r.directory_names,
    r.activities,
    r.beginning_year,
    r.end_year,
    r.nb_points,
    r.jw_per_avg,
    r.jw_act_avg,
    r.time_density,
    r.cluster_geometry,
    r.per_cluster,
    r.act_cluster,
    r.addr_name_cluster,
    r.addr_num_cluster,
    r.address_cluster,
    r.address_geometry,
    r.cluster_type,
    r.cluster_rank
FROM testing.candidates_spatial_cluster_points_printer p
JOIN testing.ranked_candidates_printer r 
  ON p.surname_searched = r.surname_searched 
  -- Ici on s'assure que le point appartient bien à la géométrie du cluster
  AND ST_Intersects(p.geom, r.cluster_geometry);
CREATE INDEX idx_points_table_printer ON testing.points_table_printer USING GIST (geom);
  END;
$$ LANGUAGE plpgsql;

----------------------------------------------------------------
-------------------------------------------------------------
-- merge tables
DROP FUNCTION IF EXISTS testing.merge_tables;

CREATE OR REPLACE FUNCTION testing.merge_tables()
RETURNS VOID AS $$
BEGIN
DROP TABLE IF EXISTS testing.final_points_table;
CREATE TABLE testing.final_points_table AS
SELECT * FROM testing.points_table_artist
UNION ALL
SELECT * FROM testing.points_table_printer;
CREATE INDEX idx_final_points_table ON testing.final_points_table USING GIST (geom);
END;
$$ LANGUAGE plpgsql;