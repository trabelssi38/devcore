BEGIN;

CREATE OR REPLACE FUNCTION devcore_set_project_archived(
    target_project text, target_user text, should_archive boolean
) RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $function$
DECLARE
    current_status text;
    project_metadata jsonb;
    member_role text;
    restored_status text;
BEGIN
    SELECT p.status,p.metadata,m.role INTO current_status,project_metadata,member_role
    FROM public.projects p
    JOIN public.project_memberships m ON m.project_id=p.id
    WHERE p.id=target_project AND m.user_id=target_user
    FOR UPDATE OF p;

    IF NOT FOUND OR member_role NOT IN ('owner','maintainer','contributor') THEN
        RAISE EXCEPTION 'Project access denied' USING ERRCODE='42501';
    END IF;
    IF (current_status='archived')=should_archive THEN
        RAISE EXCEPTION 'Project is already in the requested state' USING ERRCODE='22023';
    END IF;

    IF should_archive THEN
        UPDATE public.projects SET status='archived',
            metadata=project_metadata || jsonb_build_object('status_before_archive',current_status),
            updated_at=now() WHERE id=target_project;
        RETURN 'archived';
    END IF;

    restored_status := project_metadata->>'status_before_archive';
    IF restored_status NOT IN ('active','needs_review') OR restored_status IS NULL THEN
        restored_status := 'active';
    END IF;
    UPDATE public.projects SET status=restored_status,
        metadata=project_metadata-'status_before_archive',updated_at=now()
        WHERE id=target_project;
    RETURN restored_status;
END
$function$;

REVOKE ALL ON FUNCTION devcore_set_project_archived(text,text,boolean) FROM PUBLIC;
DO $grants$
DECLARE app_role text;
BEGIN
    FOREACH app_role IN ARRAY ARRAY['devcore_app','devcore_app_qualification'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=app_role) THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION devcore_set_project_archived(text,text,boolean) TO %I',app_role);
        END IF;
    END LOOP;
END
$grants$;

COMMIT;
