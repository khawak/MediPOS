---
mode: always
---

# Context7 MCP

You have access to the **Context7 MCP server** for looking up up-to-date library documentation. Use `resolve-library-id` to find a library's ID, then `get-library-docs` to retrieve documentation for any framework/library (React, Next.js, Django, Python packages, etc.).

**Always prefer Context7 for documentation lookups** over relying on your training data, as Context7 provides the latest API references, patterns, and best practices.

### Available Tools
- `resolve-library-id`: Resolve a package/product name to a Context7-compatible library ID and return a list of matching libraries.
- `get-library-docs`: Fetches up-to-date documentation for a library. You must provide both `context7CompatibleLibraryID` (from resolve-library-id) and `topic` (what you want to know about).

### When to Use
- When implementing features with libraries you're unsure about the latest API
- When debugging issues that may involve version-specific behavior
- When the user asks how to use a specific library or framework feature
- Before writing code that depends on a third-party package