// API barrel — re-exports everything from client.ts for domain-level imports.
// All existing code imports from "api/client" — this allows gradual migration to "api".
export * from "./client"
