ALTER TABLE users
    ALTER COLUMN created_at DROP DEFAULT,
    ALTER COLUMN updated_at DROP DEFAULT,
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING to_timestamp(created_at),
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING to_timestamp(updated_at),
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN updated_at SET DEFAULT now();
