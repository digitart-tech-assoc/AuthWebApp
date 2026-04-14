-- SQL View: v_users_with_app_role
-- app_role を動的に計算するビュー（user_memberships から）

CREATE OR REPLACE VIEW v_users_with_app_role AS
SELECT 
    u.id,
    u.user_id,
    u.discord_id,
    COALESCE(
        (SELECT membership_type FROM user_memberships 
         WHERE discord_id = u.discord_id 
         ORDER BY CASE membership_type 
           WHEN 'admin' THEN 1
           WHEN 'member' THEN 2
           WHEN 'pre_member' THEN 3
           WHEN 'obog' THEN 4
         END LIMIT 1),
        'none'
    ) as app_role,
    u.created_at,
    u.updated_at
FROM users u;
