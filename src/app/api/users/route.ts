import { db } from '@/lib/db';
import { users } from '@/lib/db/schema';
import { NextResponse } from 'next/server';
import { z } from 'zod';

const userSchema = z.object({
  name: z.string().min(2, { message: 'Name must be at least 2 characters long.' }),
  email: z.string().email({ message: 'Please enter a valid email address.' }),
});

export async function POST(request: Request) {
  try {
    const json = await request.json();
    const body = userSchema.parse(json);

    const [newUser] = await db
      .insert(users)
      .values({
        name: body.name,
        email: body.email,
      })
      .returning();

    return NextResponse.json({
      user: {
        id: newUser.id,
        name: newUser.name,
        email: newUser.email,
      },
    }, { status: 201 });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return new Response(JSON.stringify(error.errors), { status: 400 });
    }
    
    // Check for unique constraint error (specific to SQLite)
    if (error instanceof Error && error.message.includes('UNIQUE constraint failed: users.email')) {
        return NextResponse.json({ message: 'This email is already registered.' }, { status: 409 });
    }

    console.error('Error creating user:', error);
    return NextResponse.json({ message: 'An unexpected error occurred.' }, { status: 500 });
  }
}
