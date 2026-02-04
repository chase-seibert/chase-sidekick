#!/bin/bash
# migrate-to-memory.sh - Migrate from output/ to memory/

if [ -d "output" ]; then
    echo "Migrating output/ to memory/..."
    if [ -d "memory" ]; then
        echo "ERROR: memory/ directory already exists. Please resolve manually."
        exit 1
    fi
    mv output memory
    echo "✓ Migration complete! output/ → memory/"
else
    echo "No output/ directory found - nothing to migrate"
fi
