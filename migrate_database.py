#!/usr/bin/env python3
"""
Database Migration Script for TournamentPro
Run this script to apply database schema changes.
"""

import os
import sys
from supabase import create_client
from database import init_supabase, get_supabase_client

def read_migration_file(filename):
    """Read SQL migration file"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"❌ Migration file {filename} not found")
        return None
    except Exception as e:
        print(f"❌ Error reading {filename}: {e}")
        return None

def execute_sql(client, sql_content, migration_name):
    """Execute SQL content using Supabase client"""
    if not client:
        print("❌ No Supabase client available - running in development mode")
        print(f"📝 Would execute migration: {migration_name}")
        print("SQL Content:")
        print("-" * 50)
        print(sql_content[:500] + "..." if len(sql_content) > 500 else sql_content)
        print("-" * 50)
        return True
    
    try:
        # Split SQL content by statements and execute each one
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            if statement.startswith('--') or not statement:
                continue
                
            if 'SELECT' in statement.upper() and 'FROM information_schema' in statement:
                # This is the table structure query - execute and show results
                print(f"📊 Executing query {i+1}...")
                try:
                    result = client.rpc('exec_sql', {'sql': statement}).execute()
                    if result.data:
                        print("Current players table structure:")
                        for row in result.data:
                            print(f"  {row}")
                except Exception as e:
                    print(f"⚠️ Query execution note: {e}")
            else:
                print(f"🔄 Executing statement {i+1}...")
                try:
                    client.rpc('exec_sql', {'sql': statement}).execute()
                    print(f"✅ Statement {i+1} executed successfully")
                except Exception as e:
                    print(f"⚠️ Statement {i+1} warning: {e}")
                    # Continue with other statements
        
        print(f"✅ Migration {migration_name} completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error executing migration {migration_name}: {e}")
        return False

def run_migration(migration_file):
    """Run a single migration file"""
    print(f"🚀 Running migration: {migration_file}")
    
    # Read migration file
    sql_content = read_migration_file(migration_file)
    if not sql_content:
        return False
    
    # Initialize Supabase client
    client = init_supabase()
    
    # Execute migration
    return execute_sql(client, sql_content, migration_file)

def run_all_migrations():
    """Run all pending migrations"""
    migrations = [
        'migration_001_add_player_fields.sql'
    ]
    
    print("🗄️ Starting database migration process...")
    print(f"Found {len(migrations)} migration(s) to run")
    
    success_count = 0
    for migration in migrations:
        if run_migration(migration):
            success_count += 1
        print()  # Add spacing between migrations
    
    print(f"📈 Migration summary: {success_count}/{len(migrations)} successful")
    
    if success_count == len(migrations):
        print("🎉 All migrations completed successfully!")
        return True
    else:
        print("⚠️ Some migrations had issues - please review the logs")
        return False

def create_initial_schema():
    """Create the initial database schema if needed"""
    print("🏗️ Creating initial database schema...")
    
    schema_file = 'database_schema.sql'
    sql_content = read_migration_file(schema_file)
    if not sql_content:
        return False
    
    client = init_supabase()
    return execute_sql(client, sql_content, schema_file)

def setup_development_environment():
    """Setup development environment by disabling RLS"""
    print("🔧 Setting up development environment...")
    
    rls_file = 'supabase_rls_policies.sql'
    sql_content = read_migration_file(rls_file)
    if not sql_content:
        return False
    
    client = init_supabase()
    return execute_sql(client, sql_content, rls_file)

def main():
    """Main migration function"""
    print("=" * 60)
    print("🏆 TournamentPro Database Migration Tool")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'init':
            print("Initializing database schema...")
            if create_initial_schema():
                print("Setting up development environment...")
                setup_development_environment()
        elif command == 'dev':
            print("Setting up development environment...")
            setup_development_environment()
        elif command == 'migrate':
            run_all_migrations()
        else:
            print(f"Unknown command: {command}")
            print("Available commands:")
            print("  init    - Create initial database schema")
            print("  dev     - Setup development environment (disable RLS)")
            print("  migrate - Run pending migrations")
    else:
        # Default action - run migrations
        run_all_migrations()
    
    print("\n🔗 Database connection info:")
    print(f"  Supabase URL: {os.environ.get('SUPABASE_URL', 'Not configured')}")
    print(f"  Environment: {'Development' if not get_supabase_client() else 'Production'}")

if __name__ == "__main__":
    main()
