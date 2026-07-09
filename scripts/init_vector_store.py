"""
scripts/init_vector_store.py

One-time local script — creates the shared OpenAI Vector Store.

Usage:
  1. Set your OpenAI API key:
       Windows (PowerShell):  $env:OPENAI_API_KEY="sk-..."
       Linux/macOS:           export OPENAI_API_KEY="sk-..."

  2. Run from the backend/ directory:
       python scripts/init_vector_store.py

  3. Copy the vector_store_id from the output and set it on Railway:
       Railway Dashboard → Variables → OPENAI_VECTOR_STORE_ID = vs_...

DO NOT deploy this script as an endpoint.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(
            "\n❌  OPENAI_API_KEY is not set.\n"
            "    Set it in your environment before running this script.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)

    print("\n🔧  Creating OpenAI Vector Store…\n")

    vector_store = await client.vector_stores.create(
        name="KuwaitChatAI Knowledge Base",
    )

    print("✅  Vector Store created successfully!\n")
    print("─" * 60)
    print(f"  Vector Store ID : {vector_store.id}")
    print(f"  Name            : {vector_store.name}")
    print(f"  Created At      : {vector_store.created_at}")
    print("─" * 60)
    print()
    print("📋  Next steps:")
    print("    1. Copy the Vector Store ID above.")
    print("    2. Set it on Railway:")
    print("       Railway Dashboard → Variables → OPENAI_VECTOR_STORE_ID =", vector_store.id)
    print()


if __name__ == "__main__":
    asyncio.run(main())
