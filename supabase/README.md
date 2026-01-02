# Database Migrations

This folder contains SQL migration files for the Supabase database.

## Structure

- `migrations/` - SQL migration files in chronological order
- `schema.sql` - Current complete database schema (generated)
- `seed.sql` - Optional seed data for development

## How to Use

### Apply Migrations to Supabase

1. Open [Supabase SQL Editor](https://supabase.com/dashboard/project/_/sql)
2. Copy the SQL from the migration file
3. Run it in the SQL editor
4. Verify in Table Editor

### Using Supabase CLI (Recommended)

```bash
# Install Supabase CLI
npm install supabase --save-dev

# Initialize Supabase in project
npx supabase init

# Create a new migration
npx supabase migration new migration_name

# Apply migrations
npx supabase db push
```

## Migration Naming Convention

Format: `YYYYMMDD_HHMMSS_description.sql`

Examples:
- `20250121_120000_create_user_profiles.sql`
- `20250121_120100_create_bank_requisitions.sql`
- `20250121_120200_add_rls_policies.sql`

## Important Notes

- Always run migrations in order (use timestamps)
- Test migrations on a development project first
- Never modify old migrations - create new ones
- Include rollback instructions in comments
