import { migrate } from 'drizzle-orm/better-sqlite3/migrator';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import Database from 'better-sqlite3';
import { join } from 'path';
import * as dotenv from 'dotenv';

dotenv.config();

const runMigrations = async () => {
    if (!process.env.DATABASE_URL) {
        throw new Error("DATABASE_URL is not set in .env file");
    }

    try {
        const dbPath = process.env.DATABASE_URL;
        console.log(`Connecting to database at: ${dbPath}`);
        
        const dbConnection = new Database(dbPath);
        const dbInstance = drizzle(dbConnection);

        console.log("Running migrations...");
        
        await migrate(dbInstance, { migrationsFolder: join(process.cwd(), 'drizzle') });
        
        console.log("Migrations applied successfully!");
        
        dbConnection.close();
        process.exit(0);

    } catch (error) {
        console.error("Migration failed:", error);
        process.exit(1);
    }
};

runMigrations();
