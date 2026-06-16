// API barrel — re-exports everything from domain files.
// Existing code imports from "api/client" — this allows gradual migration to "api/*".
export * from "./types"
export * from "./auth"
export * from "./conversations"
export * from "./files"
export * from "./notes"
export * from "./beliefs"
export * from "./skills"
export * from "./personality"
export * from "./telemetry"
export * from "./sediment"
export * from "./notifications"
export * from "./research"
