import { z } from "zod";

/**
 * Client and server environment variable schemas with runtime validation.
 * Fails fast at startup/build time if required variables are missing or invalid.
 */
const envSchema = z.object({
  NODE_ENV: z
    .enum(["development", "test", "production"])
    .default("development"),
  NEXT_PUBLIC_APP_URL: z.string().url().default("http://localhost:3000"),
  API_INTERNAL_URL: z.string().url().default("http://127.0.0.1:8000"),
});

export type Env = z.infer<typeof envSchema>;

function validateEnv(): Env {
  const parsed = envSchema.safeParse({
    NODE_ENV: process.env.NODE_ENV,
    NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
    API_INTERNAL_URL: process.env.API_INTERNAL_URL,
  });

  if (!parsed.success) {
    const errorDetails = parsed.error.issues
      .map((issue) => `  - ${issue.path.join(".")}: ${issue.message}`)
      .join("\n");
    throw new Error(
      `Invalid environment variables:\n${errorDetails}\nCheck your .env file or deployment configuration.`,
    );
  }

  return parsed.data;
}

export const env = validateEnv();
