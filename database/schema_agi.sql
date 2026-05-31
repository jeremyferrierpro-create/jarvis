-- ==============================================================================
-- 🚀 MIGRATION SUPABASE : ARCHITECTURE AGI POUR JARVIS
-- ==============================================================================

-- Activer l'extension pgvector pour la recherche sémantique (Mémoire IA)
CREATE EXTENSION IF NOT EXISTS vector;

-- ------------------------------------------------------------------------------
-- 🧠 1. Mémoire Sémantique & Épisodique (RAG & Connaissances)
-- ------------------------------------------------------------------------------
CREATE TABLE knowledge_graph (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    categorie VARCHAR(50) NOT NULL, -- Ex: 'Dev', 'Personnel', 'Finance', 'Process'
    sujet VARCHAR(255) NOT NULL,
    contenu TEXT NOT NULL,
    embedding vector(1536), -- Pour OpenAI text-embedding-3-small (1536 dimensions)
    facteur_importance INTEGER DEFAULT 5 CHECK (facteur_importance BETWEEN 1 AND 10),
    source VARCHAR(100), -- Ex: 'auto:professionnel', 'document_ingest'
    date_assimilation TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour la recherche vectorielle (optimisation des requêtes de similarité)
CREATE INDEX ON knowledge_graph USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ------------------------------------------------------------------------------
-- ⚙️ 2. Évolution & Compétences (Les "Skills")
-- ------------------------------------------------------------------------------
CREATE TABLE jarvis_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom_skill VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    code_source TEXT NOT NULL,
    statut VARCHAR(20) DEFAULT 'actif' CHECK (statut IN ('actif', 'desactive', 'en_erreur')),
    dependances JSONB DEFAULT '[]'::JSONB,
    derniere_utilisation TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 📄 3. Traitement Documentaire
-- ------------------------------------------------------------------------------
CREATE TABLE documents_ingestes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom_fichier VARCHAR(255) NOT NULL,
    chemin_stockage VARCHAR(500),
    type_document VARCHAR(50), -- Ex: 'pdf', 'image', 'code'
    categorie_ia VARCHAR(50), -- Ex: 'prive', 'travail', 'apprentissage'
    resume_cognitif TEXT,
    donnees_sensibles BOOLEAN DEFAULT FALSE,
    confiance_classification FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 👥 4. Relation Humain-Machine & Profiling
-- ------------------------------------------------------------------------------
CREATE TABLE human_relationship (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utilisateur_id VARCHAR(50) DEFAULT 'jeremy',
    humeur_courante VARCHAR(50), -- Ex: 'Stressé', 'Joyeux', 'Focus'
    relation_score FLOAT DEFAULT 0.0 CHECK (relation_score BETWEEN -100 AND 100),
    preferences JSONB DEFAULT '{}'::JSONB,
    derniere_analyse TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insérer le profil par défaut de Jérémy
INSERT INTO human_relationship (utilisateur_id, relation_score, humeur_courante) 
VALUES ('jeremy', 10.0, 'Neutre')
ON CONFLICT DO NOTHING;

-- ------------------------------------------------------------------------------
-- 🎙️ 5. Capteurs Environnementaux
-- ------------------------------------------------------------------------------
CREATE TABLE environment_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contexte_sonore VARCHAR(100) NOT NULL, -- Ex: 'Frappes clavier', 'Silence', 'Voix'
    volume_rms FLOAT NOT NULL,
    zero_crossing_rate FLOAT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 🛠️ 6. Autonomie : File d'attente des tâches
-- ------------------------------------------------------------------------------
CREATE TABLE system_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    description TEXT NOT NULL,
    statut VARCHAR(50) DEFAULT 'en_attente' CHECK (statut IN ('en_attente', 'en_cours', 'termine', 'echoue')),
    contexte JSONB DEFAULT '{}'::JSONB,
    date_creation TIMESTAMPTZ DEFAULT NOW(),
    date_echeance TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- ⚠️ 7. Résilience : Auto-Correction et Logs d'erreurs
-- ------------------------------------------------------------------------------
CREATE TABLE error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_erreur TEXT NOT NULL,
    stack_trace TEXT,
    contexte VARCHAR(255), -- Ex: 'skill_budget', 'document_ingest'
    resolu BOOLEAN DEFAULT FALSE,
    date_occurence TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- 🔄 TRIGGERS POUR LA MISE À JOUR DE `updated_at`
-- ==============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_knowledge_graph_modtime
    BEFORE UPDATE ON knowledge_graph
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jarvis_skills_modtime
    BEFORE UPDATE ON jarvis_skills
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_human_relationship_modtime
    BEFORE UPDATE ON human_relationship
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_tasks_modtime
    BEFORE UPDATE ON system_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==============================================================================
-- 🛡️ POLITIQUES DE SÉCURITÉ RLS (Row Level Security) - OPTIONNEL
-- ==============================================================================
-- Si vous utilisez l'API anonyme, il est recommandé de sécuriser l'accès.
-- Actuellement en mode ouvert pour le MVP local.

ALTER TABLE knowledge_graph ENABLE ROW LEVEL SECURITY;
ALTER TABLE jarvis_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents_ingestes ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_relationship ENABLE ROW LEVEL SECURITY;
ALTER TABLE environment_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE error_logs ENABLE ROW LEVEL SECURITY;

-- Autoriser tout accès anonyme (car JARVIS tourne en local avec la clé anon)
CREATE POLICY "Allow all access" ON knowledge_graph FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access" ON jarvis_skills FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access" ON documents_ingestes FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access" ON human_relationship FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access" ON environment_logs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access" ON system_tasks FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access" ON error_logs FOR ALL USING (true) WITH CHECK (true);
