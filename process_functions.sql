-- Creation des tables necessaires
DROP TABLE IF EXISTS testing.candidates;

CREATE TABLE IF NOT EXISTS testing.candidates (
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
CREATE INDEX IF NOT EXISTS idx_candidates_per ON testing.candidates (per);
CREATE INDEX IF NOT EXISTS idx_candidates_act ON testing.candidates(act);
CREATE INDEX IF NOT EXISTS idx_candidates_pub_year ON testing.candidates (pub_year);
CREATE INDEX IF NOT EXISTS idx_candidates_surname_searched ON testing.candidates (surname_searched);
CREATE INDEX IF NOT EXISTS idx_candidates_first_name_searched ON testing.candidates (first_name_searched);
CREATE INDEX IF NOT EXISTS idx_candidates_geom ON testing.candidates USING GIST (geom);
------------------------------------------------------------------------
DROP TABLE IF EXISTS testing.candidates_cluster_points;

CREATE TABLE IF NOT EXISTS testing.candidates_cluster_points (
    uri_agent CHARACTER VARYING,
    uuid CHARACTER VARYING,
	cluster_id INTEGER,
    cluster_uuid_ref UUID,
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

CREATE INDEX IF NOT EXISTS idx_candidates_cluster_points_geom ON testing.candidates_cluster_points USING GIST (geom);
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
    first_name_searched CHARACTER VARYING,
    -- Colonnes issues de testing.ranked_candidates (alias r)
    uuid_cluster CHARACTER VARYING, 
    directory_names CHARACTER VARYING, 
    activities CHARACTER VARYING,
    beginning_year BIGINT,
    end_year BIGINT,
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
    cluster_rank BIGINT
);
CREATE INDEX IF NOT EXISTS idx_final_points_table ON testing.final_points_table USING GIST (geom);

-- Function de flitrage préalable des candidats
DROP FUNCTION IF EXISTS testing.filter_candidates;

CREATE OR REPLACE FUNCTION testing.filter_candidates (
uri CHARACTER VARYING,
surname CHARACTER VARYING,
first_name CHARACTER VARYING DEFAULT '',
debut BIGINT DEFAULT 1800,
fin BIGINT DEFAULT 1950,
filtre TEXT DEFAULT ''
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
    AND (unaccent(ad.act) ~* filtre);

END;
$$ LANGUAGE plpgsql;

-- Function de clustering
DROP FUNCTION IF EXISTS testing.clustering;

CREATE OR REPLACE FUNCTION testing.clustering(
    surname CHARACTER VARYING,
    first_name CHARACTER VARYING DEFAULT NULL
	)
RETURNS TABLE (
    uri_agent CHARACTER VARYING,
    uuid CHARACTER VARYING,
    cluster_id INTEGER,
    cluster_uuid_ref UUID,
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
        NULL::UUID AS cluster_uuid_ref,
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
    FROM testing.candidates ca
    WHERE ca.surname_searched = surname;
END;
$$ LANGUAGE plpgsql;

--Function de calcul de metadonnees sur les clusters
DROP FUNCTION IF EXISTS testing.cluster_metadata;

CREATE OR REPLACE FUNCTION testing.cluster_metadata()
RETURNS VOID AS $$
BEGIN
	CREATE INDEX IF NOT EXISTS idx_spatial_points ON testing.candidates_cluster_points (cluster_id);
    DROP TABLE IF EXISTS testing.candidates_clusters;

    CREATE TABLE testing.candidates_clusters AS
    SELECT 
            gen_random_uuid() as uuid_cluster,
            cluster_id,
            uri_agent,
            MAX(clustered_entries.surname_searched) AS surname_searched,
            MAX(clustered_entries.first_name_searched) AS first_name_searched,
            string_agg(DISTINCT clustered_entries.per, ' | ') AS directory_names,
            string_agg(DISTINCT clustered_entries.act, ' | ') AS activities,
            MIN(pub_year) AS beginning_year,
            MAX(pub_year) AS end_year,
            COUNT(*) AS nb_points,
            ROUND(AVG(jarowinkler_per), 3) AS jw_per_avg,
            ROUND(AVG(jarowinkler_act), 3) AS jw_act_avg,
            ROUND(
                COUNT(*)::NUMERIC / 
                NULLIF((MAX(pub_year) - MIN(pub_year) + 1), 0), 2
            ) AS time_density,
            ST_Collect(clustered_entries.geom)::GEOMETRY(MultiPoint, 4326) AS cluster_geometry,
            mode() WITHIN GROUP (ORDER BY per) AS per_cluster,
            mode() WITHIN GROUP (ORDER BY act) AS act_cluster,
            MAX(most_frequent_address.addr_name) AS addr_name_cluster,
            MAX(most_frequent_address.addr_num) AS addr_num_cluster,
            concat_ws(' ', MAX(most_frequent_address.addr_num), MAX(most_frequent_address.addr_name)) AS address_cluster,
            MAX(most_frequent_address.geom) AS address_geometry
        FROM testing.candidates_cluster_points AS clustered_entries
        LEFT JOIN LATERAL (
            -- Sélection de l'adresse la plus fréquence dans ce cluster
            SELECT addr_name, addr_num, geom, COUNT(*) AS freq
            FROM testing.candidates_cluster_points
            WHERE uri_agent = clustered_entries.uri_agent 
            AND cluster_id = clustered_entries.cluster_id
            GROUP BY addr_name, addr_num, geom
            ORDER BY freq DESC
            LIMIT 1
        ) AS most_frequent_address
        ON true
        WHERE cluster_id IS NOT NULL 	
        -- EDIT Bertrand
        -- GROUP BY uri_agent, surname_searched, first_name_searched, cluster_id
        GROUP BY uri_agent, cluster_id;

    -- Assigne la référence de l'UUID du cluster à chaque entrée clusterisée
	UPDATE testing.candidates_cluster_points AS pts
	    SET cluster_uuid_ref = clu.uuid_cluster
	    FROM testing.candidates_clusters AS clu
	    WHERE pts.uri_agent = clu.uri_agent
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
    INSERT INTO testing.final_points_table (
        uri_agent,
        uuid,
        cluster_id, 
        per, 
        jarowinkler_per, 
        act, 
        jarowinkler_act,
        pub_year, 
        beginning_year_calc, 
        end_year_calc, 
        directory, 
        collection,
        addr_num, 
        addr_name, 
        address, 
        geo_source, 
        view_link, 
        geom,
        surname_searched, 
        first_name_searched, 
        uuid_cluster, 
        directory_names,
        activities, 
        beginning_year, 
        end_year, 
        nb_points, 
        jw_per_avg, 
        jw_act_avg,
        time_density, 
        cluster_geometry, 
        per_cluster, 
        act_cluster,
        addr_name_cluster, 
        addr_num_cluster,
        address_cluster, 
        address_geometry, 
        cluster_type, 
        cluster_rank
    )
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
    FROM testing.candidates_cluster_points a -- entrées d'annuaire
    JOIN testing.ranked_candidates r  -- clusters triés
      ON a.cluster_uuid_ref = r.uuid_cluster;

    RAISE NOTICE 'Insertion des données dans testing.final_points_table terminée avec succès.';
END;
$$ LANGUAGE plpgsql;