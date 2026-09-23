--  ########################################
-- PREPARATION DE LA TABLE ALL_DATA
--  ########################################
-- ATTENTION : N'EXECUTER QU'UNE SEULE FOIS

-- Ajout d'un UUID pour chaque ligne de la table 
ALTER TABLE testing.all_data ADD COLUMN uuid UUID;
UPDATE testing.all_data SET uuid = gen_random_uuid();

-- Création d'une version sans accents des élements PER et ACT
ALTER TABLE testing.all_data ADD COLUMN per_unaccent CHARACTER VARYING;
ALTER TABLE testing.all_data ADD COLUMN act_unaccent CHARACTER VARYING;
UPDATE testing.all_data SET per_unaccent = unaccent(per);
UPDATE testing.all_data SET act_unaccent = unaccent(act);

-- Création d'index sur ces nouvelles colonne 
CREATE INDEX IF NOT EXISTS idx_uuid ON testing.all_data (uuid);
CREATE INDEX IF NOT EXISTS idx_per_unaccent ON testing.all_data USING gin (per_unaccent gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_act_unaccent ON testing.all_data USING gin (act_unaccent gin_trgm_ops);

--  ########################################
--  CRÉATION DES TABLES NÉCESSAIRES
--  ########################################


DROP TABLE IF EXISTS testing.candidates;

CREATE TABLE IF NOT EXISTS testing.candidates (
    agent_uri CHARACTER VARYING,
    agent_type CHARACTER VARYING,
	beginning_year_calc BIGINT,
	end_year_calc BIGINT,
    surname_searched CHARACTER VARYING,
	first_name_searched CHARACTER VARYING,
    uuid UUID
    -- Temporairement désactivée à cause des doublons d'agent uri créés par les cas "Père & Fils"
    --PRIMARY KEY (agent_uri, agent_type, uuid)
    );

CREATE INDEX IF NOT EXISTS idx_candidates_uuid ON testing.candidates (uuid);



------------------------------------------------------------------------
DROP TABLE IF EXISTS testing.candidates_cluster_points;

CREATE TABLE IF NOT EXISTS testing.candidates_cluster_points (
    -- Clé primaire
    agent_uri CHARACTER VARYING,
    agent_type CHARACTER VARYING,
    uuid UUID,

    -- Informations du cluster
	cluster_id INTEGER,
    cluster_uuid_ref UUID,
   	jarowinkler_per NUMERIC,
    jarowinkler_act NUMERIC,
    
    -- Information de requête
	beginning_year_calc INTEGER,
	end_year_calc INTEGER,
    surname_searched CHARACTER VARYING,
	first_name_searched CHARACTER VARYING

	);

CREATE INDEX IF NOT EXISTS idx_candidates_cluster_points_uuid ON testing.candidates_cluster_points (uuid);


-- CREATE INDEX IF NOT EXISTS idx_candidates_cluster_points_geom ON testing.candidates_cluster_points USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_candidates_cluster_cluster_id ON testing.candidates_cluster_points (cluster_id);


-------------------------------------------------------------------------------
DROP TABLE IF EXISTS testing.candidates_cluster_metadata;

CREATE TABLE IF NOT EXISTS testing.candidates_cluster_metadata (
        uuid_cluster CHARACTER VARYING, -- gen_random_uuid() as uuid_cluster,
        uri_agent CHARACTER VARYING, -- uri_agent,
        surname_searched CHARACTER VARYING,
        first_name_searched CHARACTER VARYING,
        cluster_id INTEGER,
        directory_names CHARACTER VARYING,
        activities CHARACTER VARYING,
        beginning_year BIGINT,
        end_year BIGINT,
        nb_points INTEGER,
        jw_per_avg NUMERIC,
        jw_act_avg NUMERIC,
        time_density NUMERIC,
        cluster_geometry GEOMETRY(MultiPoint, 4326), -- Géométrie Multipoint du cluster
        -- Entrée "de synthèse"
        per_cluster CHARACTER VARYING,
        act_cluster CHARACTER VARYING,
        addr_name_cluster CHARACTER VARYING,
        addr_num_cluster CHARACTER VARYING,
        address_cluster CHARACTER VARYING,
        address_geometry GEOMETRY -- Géométrie de l'adresse la plus fréquente.
);

CREATE INDEX IF NOT EXISTS idx_candidates_cluster_metadata_cluster_geometry ON testing.candidates_cluster_metadata USING GIST (cluster_geometry);
CREATE INDEX IF NOT EXISTS idx_candidates_cluster_metadata_uuid_cluster ON testing.candidates_cluster_metadata (uuid_cluster);

-------------------------------------------------------------------------------------
DROP TABLE IF EXISTS testing.final_points_table;

CREATE TABLE testing.final_points_table (
    -- Colonnes issues de testing.candidates_cluster_points (alias a)
    agent_uri CHARACTER VARYING,
    agent_type CHARACTER VARYING,
    uuid UUID,
    cluster_id INTEGER,
    per CHARACTER VARYING,
    jarowinkler_per NUMERIC,
    act CHARACTER VARYING,
    jarowinkler_act NUMERIC,
    pub_year INTEGER,
    beginning_year_calc INTEGER,
    end_year_calc INTEGER,
    directory CHARACTER VARYING,
    collection CHARACTER VARYING,
    addr_num CHARACTER VARYING,
    addr_name CHARACTER VARYING,
    address CHARACTER VARYING,
    geo_source CHARACTER VARYING,
    view_link CHARACTER VARYING,
    geom GEOMETRY(Point, 4326),
    surname_searched CHARACTER VARYING,
    first_name_searched CHARACTER VARYING,
    -- Colonnes issues de testing.ranked_candidates (alias r)
    uuid_cluster UUID, 
    directory_names CHARACTER VARYING, 
    activities CHARACTER VARYING,
    beginning_year INTEGER,
    end_year INTEGER,
    nb_points INTEGER,
    jw_per_avg NUMERIC,
    jw_act_avg NUMERIC,
    time_density NUMERIC,          -- Ajuster en DOUBLE PRECISION si nécessaire
    cluster_geometry GEOMETRY (MULTIPOINT, 4326), 
    per_cluster CHARACTER VARYING,
    act_cluster CHARACTER VARYING,
    addr_name_cluster CHARACTER VARYING,
    addr_num_cluster CHARACTER VARYING,
    address_cluster CHARACTER VARYING, -- Temporairement désactivé
    address_geometry GEOMETRY,

    -- Colonnes calculées via la fonction rank_candidates
    cluster_type TEXT,
    cluster_rank INTEGER
);
CREATE INDEX IF NOT EXISTS idx_final_points_table ON testing.final_points_table USING GIST (geom);


--  ########################################
--  FONCTION DE FILTRAGE PRÉALABLE DES CANDIDATS
--  ########################################

DROP FUNCTION IF EXISTS testing.filter_candidates;

CREATE OR REPLACE FUNCTION testing.filter_candidates (
    uri_agent CHARACTER VARYING,
    type_agent CHARACTER VARYING,
    filtre CHARACTER VARYING,
    surname CHARACTER VARYING,
    first_name CHARACTER VARYING DEFAULT '',
    debut INTEGER DEFAULT 1800,
    fin INTEGER DEFAULT 1950
)
RETURNS TABLE(
    agent_uri CHARACTER VARYING,
    agent_type CHARACTER VARYING,
	beginning_year_calc_out INTEGER,
	end_year_calc_out INTEGER,
    surname_searched CHARACTER VARYING,
	first_name_searched CHARACTER VARYING,
    uuid UUID
)
AS $$
DECLARE
	intervalle INTEGER;
	x INTEGER;
	beginning_year_calc INTEGER;
	end_year_calc INTEGER;
	intervalle_calc INTEGER;
BEGIN
    IF type_agent NOT IN ('dessinateur', 'imprimeur') THEN
        RAISE EXCEPTION 'Type d''agent non reconnu : %', agent_type;
    END IF;

	intervalle := fin-debut;
	IF 
		intervalle < 10 THEN
		x := ROUND((10-intervalle)/2);
		beginning_year_calc := debut-x;
		end_year_calc := fin+(10-intervalle-x);
	ELSE 
		beginning_year_calc := debut;
		end_year_calc := fin;
	END IF;
	
	RETURN QUERY
	SELECT
    uri_agent,
    type_agent,
    beginning_year_calc,
	end_year_calc,
	surname,
	first_name,
    ad.uuid
    FROM testing.all_data AS ad
    WHERE 
        ad."source.publication_year" BETWEEN beginning_year_calc AND end_year_calc
    AND
        -- EDIT BERTRAND : On travaille directement sur les champs désaccentués pour profiter des index et accélérer le filtrage
        per_unaccent ILIKE ('%' || unaccent(surname) || '%')
    AND act_unaccent ~* filtre;
END;
$$ LANGUAGE plpgsql;

--  ########################################
--  FONCTION DE CLUSTERING
--  ########################################

DROP FUNCTION IF EXISTS testing.clustering;

CREATE OR REPLACE FUNCTION testing.clustering(
    uri_agent CHARACTER VARYING,
    type_agent CHARACTER VARYING
	)
RETURNS TABLE (
    agent_uri CHARACTER VARYING,
    agent_type CHARACTER VARYING,
    uuid UUID,
    cluster_id INTEGER,
    cluster_uuid_ref UUID,
    jarowinkler_per NUMERIC,
	jarowinkler_act NUMERIC,
    beginning_year_calc INTEGER,
	end_year_calc INTEGER,
    surname_searched CHARACTER VARYING,
	first_name_searched CHARACTER VARYING
) 
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ca.agent_uri,
		ca.agent_type,
        ca.uuid,
        -- 1. Clustering spatial (EPS 50m)
        ST_ClusterDBSCAN(ST_Transform(ad.geom, 2154), eps := 50, minpoints := 2) OVER()::INTEGER AS cluster_id,
        NULL::UUID AS cluster_uuid_ref,
        -- 2. Calcul du meilleur score JW (Argmax)
        GREATEST(
            jarowinkler(testing.normalize_per(ad.per), testing.normalize_per(ca.surname_searched)),
			CASE
				WHEN ca.first_name_searched <> '' THEN
            		jarowinkler(testing.normalize_per(ad.per), testing.normalize_per(ca.surname_searched || ' ' || ca.first_name_searched))
				ELSE 0
			END
        )::NUMERIC AS jarowinkler_per,
		-- Score Métier unique (Meilleur score parmi tous les mots-clés)
        -- QUESTION BERTRAND : ADAPTER AU TYPE d'AGENT ?
        GREATEST(
            jarowinkler(ad.act_unaccent, 'peintre'), jarowinkler(ad.act_unaccent, 'artiste'),
			jarowinkler(ad.act_unaccent, 'peintre-artiste'), jarowinkler(ad.act_unaccent, 'artiste-peintre'),
            jarowinkler(ad.act_unaccent, 'architecte'), jarowinkler(ad.act_unaccent, 'dessinateur'),
            jarowinkler(ad.act_unaccent, 'affiche'), jarowinkler(ad.act_unaccent, 'imprimerie'), 
            jarowinkler(ad.act_unaccent, 'typographe'), jarowinkler(ad.act_unaccent, 'lithographe'), 
            jarowinkler(ad.act_unaccent, 'graveur'), jarowinkler(ad.act_unaccent, 'imprimeur'),
			jarowinkler(ad.act_unaccent, 'imprimeur-lithographe'), jarowinkler(ad.act_unaccent, 'imprimeur-typographe')
        )::NUMERIC AS jarowinkler_act,
		ca.beginning_year_calc,
		ca.end_year_calc,
		ca.surname_searched,
		ca.first_name_searched
    FROM testing.candidates ca
    JOIN testing.all_data ad 
    ON ca.uuid = ad.uuid
    WHERE ca.agent_uri = uri_agent
	AND ca.agent_type = type_agent;
END;
$$ LANGUAGE plpgsql;

--  ########################################
--  FONCTION DE CALCUL DE MÉTADONNÉES SUR LES CLUSTERS
--  ########################################

DROP FUNCTION IF EXISTS testing.cluster_metadata;

CREATE OR REPLACE FUNCTION testing.cluster_metadata()
RETURNS VOID AS $$
BEGIN
    DROP TABLE IF EXISTS testing.candidates_clusters;

    CREATE TABLE testing.candidates_clusters AS
    SELECT 
            gen_random_uuid()::UUID as uuid_cluster,
            cluster_id,
            agent_uri,
            agent_type,
            MAX(clustered_entries.surname_searched) AS surname_searched,
            MAX(clustered_entries.first_name_searched) AS first_name_searched,
            string_agg(DISTINCT ad.per, ' | ') AS directory_names,
            string_agg(DISTINCT ad.act, ' | ') AS activities,
            MIN(ad."source.publication_year") AS beginning_year,
            MAX(ad."source.publication_year") AS end_year,
            COUNT(*) AS nb_points,
            ROUND(AVG(jarowinkler_per), 3) AS jw_per_avg,
            ROUND(AVG(jarowinkler_act), 3) AS jw_act_avg,
            ROUND(
                COUNT(*)::NUMERIC / 
                NULLIF((MAX(ad."source.publication_year") - MIN(ad."source.publication_year") + 1), 0), 2
            ) AS time_density,
            ST_Collect(ad.geom)::GEOMETRY(MultiPoint, 4326) AS cluster_geometry,
            mode() WITHIN GROUP (ORDER BY ad.per) AS per_cluster,
            mode() WITHIN GROUP (ORDER BY ad.act) AS act_cluster,
            MAX(most_frequent_address."address.name") AS addr_name_cluster,
            MAX(most_frequent_address."address.number") AS addr_num_cluster,
            concat_ws(' ', MAX(most_frequent_address."address.number"), MAX(most_frequent_address."address.name")) AS address_cluster,
            MAX(most_frequent_address.geom) AS address_geometry
        FROM testing.candidates_cluster_points AS clustered_entries
		JOIN testing.all_data AS ad
		ON ad.uuid = clustered_entries.uuid
        LEFT JOIN LATERAL (
            -- Sélection de l'adresse la plus fréquence dans ce cluster
            SELECT "address.name", "address.number", geom, COUNT(*) AS freq
            FROM testing.candidates_cluster_points
            JOIN testing.all_data
            ON all_data.uuid = candidates_cluster_points.uuid
            WHERE agent_uri = clustered_entries.agent_uri 
            AND agent_type = clustered_entries.agent_type
            AND cluster_id = clustered_entries.cluster_id
            GROUP BY "address.name", "address.number", geom
            ORDER BY freq DESC
            LIMIT 1
        ) AS most_frequent_address
        ON true
        WHERE cluster_id IS NOT NULL
        GROUP BY agent_uri, cluster_id, agent_type;

    -- Assigne la référence de l'UUID du cluster à chaque entrée clusterisée
	UPDATE testing.candidates_cluster_points AS pts
	    SET cluster_uuid_ref = clu.uuid_cluster
	    FROM testing.candidates_clusters AS clu
	    WHERE pts.agent_uri = clu.agent_uri
	      AND pts.cluster_id = clu.cluster_id;
		  
    CREATE INDEX idx_clusters_multipoint_geom ON testing.candidates_clusters USING GIST (cluster_geometry);
    CREATE INDEX idx_clusters_multipoint_jw ON testing.candidates_clusters (jw_act_avg, jw_per_avg);
    RAISE NOTICE 'Table testing.candidates_clusters créée avec succès.';
END;
$$ LANGUAGE plpgsql;

-----------------------------------------------------

DROP FUNCTION IF EXISTS testing.rank_candidates;

CREATE OR REPLACE FUNCTION testing.rank_candidates()
RETURNS VOID AS $$
BEGIN
    DROP TABLE IF EXISTS testing.ranked_candidates;

    CREATE TABLE testing.ranked_candidates AS
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
    FROM testing.candidates_clusters;

    CREATE INDEX idx_ranked_candidates_surname ON testing.ranked_candidates (surname_searched);
    RAISE NOTICE 'Table testing.ranked_candidates créée avec succès.';
END;
$$ LANGUAGE plpgsql;

---------------------
-----------------------

DROP FUNCTION IF EXISTS testing.keep_results;

CREATE OR REPLACE FUNCTION testing.keep_results()
RETURNS VOID AS $$
BEGIN
    -- Insertion des données dans la table déjà existante
    INSERT INTO testing.final_points_table
    SELECT 
        a.agent_uri,
		a.agent_type,
        a.uuid,
        a.cluster_id,
        ad.per,
        a.jarowinkler_per,
        ad.act,
        a.jarowinkler_act,
        ad."source.publication_year",
        a.beginning_year_calc,
        a.end_year_calc,
        ad."source.book",
        ad."source.collection",
        ad."address.number",
        ad."address.name",
		trim(concat_ws(' ',ad."address.number", ad."address.name")),
        ad."geocoding.response.source",
        ad."source.view_link",
        ad.geom,
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
    FROM testing.candidates_cluster_points a -- entrées d'annuaire
    JOIN testing.ranked_candidates r  -- clusters triés
      ON a.cluster_uuid_ref = r.uuid_cluster
    JOIN testing.all_data ad
	  ON a.uuid = ad.uuid;
    RAISE NOTICE 'Insertion des données dans testing.final_points_table terminée avec succès.';
END;
$$ LANGUAGE plpgsql;
