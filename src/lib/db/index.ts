import { drizzle } from 'drizzle-orm/better-sqlite3';
import Database from 'better-sqlite3';
import * as schema from './schema';
import * as dotenv from 'dotenv';

dotenv.config();

if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL is not set');
}

const sqlite = new Database(process.env.DATABASE_URL);

// For enabling WAL mode, which is good for concurrency.
sqlite.pragma('journal_mode = WAL');

export const db = drizzle(sqlite, { schema, logger: true });
