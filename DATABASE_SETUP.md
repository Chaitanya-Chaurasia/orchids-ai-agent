# Database Setup with Drizzle ORM and SQLite

This guide walks you through the new database setup in your Next.js project.

## 1. Install Dependencies

First, you need to install the required packages for Drizzle ORM and SQLite. Open your terminal and run:

```bash
npm install drizzle-orm drizzle-kit better-sqlite3 dotenv
npm install -D @types/better-sqlite3 tsx
```
_or use your preferred package manager (`pnpm`, `yarn`)._

`tsx` is a tool for running TypeScript files directly, which we'll use for our migration script.

## 2. Add Scripts to `package.json`

Add the following scripts to your `package.json` file to easily manage your database migrations:

```json
"scripts": {
  // ... your other scripts
  "db:generate": "drizzle-kit generate:sqlite",
  "db:migrate": "tsx src/lib/db/migrate.ts",
  "db:studio": "drizzle-kit studio"
}
```

- `db:generate`: Generates SQL migration files based on changes in your schema (`src/lib/db/schema.ts`).
- `db:migrate`: Applies the generated migrations to your database.
- `db:studio`: Opens a local web UI to browse and query your database.

## 3. Update .gitignore

A `.env` file has been created with the `DATABASE_URL`. Make sure this file and the database file itself are not committed to version control. Add the following lines to your `.gitignore` file:

```
# Local Environment
.env
.env.local

# Database
*.db
*.db-journal

# Drizzle
drizzle/
```

## 4. Run Initial Migration

Everything is set up to create your database tables. Run the migration script:

```bash
npm run db:migrate
```

This command executes `src/lib/db/migrate.ts`, which applies all migrations from the `drizzle` folder to your `sqlite.db` file. An initial migration for the `users` and `posts` tables has already been created for you.

## 5. How to Use

### Making Schema Changes

1.  Modify the schema file at `src/lib/db/schema.ts`.
2.  Run `npm run db:generate` to create a new migration file in the `drizzle` directory.
3.  Review the generated SQL file to ensure it's correct.
4.  Run `npm run db:migrate` to apply the changes to your database.

### Querying the Database

You can now import the `db` instance from `src/lib/db/index.ts` in your server-side code (e.g., API routes, Server Components, `getServerSideProps`) to interact with your database.

**Example: `src/app/api/users/route.ts`**
```typescript
import { db } from '@/lib/db';
import { users } from '@/lib/db/schema';
import { NextResponse } from 'next/server';

export async function GET() {
  const allUsers = await db.select().from(users);
  return NextResponse.json(allUsers);
}
```

That's it! Your Next.js application is now configured with a SQLite database using Drizzle ORM.
