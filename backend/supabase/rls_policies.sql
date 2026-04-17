-- ============================================================
-- VYUD LMS — Row Level Security policies
-- Apply: paste into Supabase SQL Editor and run.
-- ============================================================
--
-- CURRENT SCHEMA LIMITATION:
-- knowledge_nodes and knowledge_edges are course-scoped, not user-scoped.
-- Until a `owner_id` column is added to `courses` (and propagated to nodes),
-- full per-user isolation is not possible for the graph data.
--
-- STEP 1 — Add owner_id to courses (run once, then update app code):
--
--   ALTER TABLE courses ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES auth.users(id);
--   UPDATE courses SET owner_id = (SELECT id FROM auth.users LIMIT 1); -- backfill
--   ALTER TABLE courses ALTER COLUMN owner_id SET NOT NULL;
--
-- After that, run STEP 2 below.
-- ============================================================

-- ============================================================
-- STEP 2 — Enable RLS and create policies
-- ============================================================

-- Users table: each row is a user; they can only read/update their own record.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_select_own" ON users
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "users_update_own" ON users
    FOR UPDATE USING (auth.uid()::text = id::text);

-- Courses: owner can do anything; others can read (for shared courses).
-- Requires owner_id column (see STEP 1 above).
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "courses_owner_all" ON courses
    FOR ALL USING (auth.uid() = owner_id);

CREATE POLICY "courses_read_public" ON courses
    FOR SELECT USING (true);  -- remove this line if courses should be private

-- Knowledge nodes: inherit access from their parent course.
ALTER TABLE knowledge_nodes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "nodes_owner_all" ON knowledge_nodes
    FOR ALL USING (
        course_id IN (
            SELECT id FROM courses WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY "nodes_read_public" ON knowledge_nodes
    FOR SELECT USING (true);  -- remove if nodes should be private

-- Knowledge edges: same as nodes — scoped to course ownership.
ALTER TABLE knowledge_edges ENABLE ROW LEVEL SECURITY;

CREATE POLICY "edges_owner_all" ON knowledge_edges
    FOR ALL USING (
        source_id IN (
            SELECT kn.id FROM knowledge_nodes kn
            JOIN courses c ON kn.course_id = c.id
            WHERE c.owner_id = auth.uid()
        )
    );

CREATE POLICY "edges_read_public" ON knowledge_edges
    FOR SELECT USING (true);  -- remove if edges should be private

-- Lessons: scoped to course ownership.
ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;

CREATE POLICY "lessons_owner_all" ON lessons
    FOR ALL USING (
        course_id IN (
            SELECT id FROM courses WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY "lessons_read_public" ON lessons
    FOR SELECT USING (true);  -- remove if lessons should be private
