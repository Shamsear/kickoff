# Database Migration: Player Goals Tracking

This migration adds support for individual player goal tracking in team tournaments, enabling two different scoring systems:

## Changes Made

### 1. Matches Table Updates
- Added `team1_player_goals` (INTEGER, nullable) - Goals scored by team1's selected player
- Added `team2_player_goals` (INTEGER, nullable) - Goals scored by team2's selected player
- Added check constraints to ensure goals are non-negative
- Added index for better query performance

### 2. Tournaments Table Updates
- Added `scoring_system` (VARCHAR(20), default 'win_based') - Determines how team scores are calculated
- Added check constraint to ensure valid scoring systems ('goal_based' or 'win_based')

### 3. Players Table Updates
- Ensured basic required columns exist: `id`, `team_id`, `tournament_id`, `name`, `jersey_number`, `position`, `email`, `phone`, `gamer_tag`
- Added constraints for jersey number uniqueness within teams
- Cleaned up schema by removing unused complex fields

## Scoring Systems

### Goal-Based Scoring
- Team score = Total goals scored by their player
- Teams ranked by total goals across all matches
- Individual match winner still determined by who scored more goals

### Win-Based Scoring  
- Team score = Match points (3 for win, 1 for draw, 0 for loss)
- Teams ranked by match points, then goal difference
- Individual match winner determined by who scored more goals

## Migration Steps

### Option 1: Using Supabase Dashboard
1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. **First, check your current schema**: Copy and paste content from `check_players_schema.sql` and execute
4. **If players table doesn't exist or has wrong columns**: Copy and paste content from `create_minimal_players_table.sql` and execute
5. Copy and paste the content from `add_player_goals_fields.sql` and execute
6. Copy and paste the content from `update_players_table.sql` and execute (if needed)

### Option 2: Using Supabase CLI
```bash
# If you have Supabase CLI installed
supabase db push
```

### Option 3: Manual SQL Execution
Connect to your PostgreSQL database and run:
```sql
-- Run the contents of add_player_goals_fields.sql
```

## Verification

After running the migration, verify the changes:

```sql
-- Check new columns exist
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'matches' 
AND column_name IN ('team1_player_goals', 'team2_player_goals');

-- Check tournaments table
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'tournaments' 
AND column_name = 'scoring_system';

-- Check constraints
SELECT conname, contype, confrelid::regclass, pg_get_constraintdef(oid)
FROM pg_constraint 
WHERE conrelid = 'matches'::regclass
AND conname LIKE '%player_goals%';
```

## Backward Compatibility

- All new fields are nullable, so existing matches will work without modification
- Existing tournaments will default to 'win_based' scoring system
- The application handles both old matches (without player goals) and new matches gracefully

## Data Migration (if needed)

If you have existing match data and want to populate the new fields:

```sql
-- For goal-based tournaments, copy team scores to player goals
UPDATE matches 
SET team1_player_goals = team1_score,
    team2_player_goals = team2_score
WHERE tournament_id IN (
    SELECT id FROM tournaments WHERE scoring_system = 'goal_based'
)
AND team1_player_goals IS NULL;

-- For win-based tournaments, you may need to manually set player goals
-- based on your business logic or leave them as NULL
```

## Application Changes

The following application components have been updated to support these changes:

1. **Match Result Form** (`templates/tournament/match_result.html`)
   - Added individual player goal inputs for team tournaments
   - Dynamic score calculation based on scoring system
   - Real-time preview of match results

2. **Backend Route** (`routes/tournament.py`)
   - `save_match_result()` now handles player goals
   - Team score calculation based on scoring system
   - Winner determination based on actual goals scored

3. **Standings Calculation** (`routes/tournament.py`)
   - `calculate_standings()` updated for both scoring systems
   - Proper goal statistics using individual player goals
   - Flexible sorting based on tournament type

4. **Database Layer** (`database.py`)
   - Mock data updated to include new fields
   - Flexible score update handling

## Testing

Test both scoring systems with sample data:

1. Create a goal-based team tournament
2. Create a win-based team tournament  
3. Enter match results with different goal combinations
4. Verify standings are calculated correctly
5. Check that player vs player matchups display properly

## Troubleshooting

### Error: "Could not find the 'address' column"
**Solution**: The application was trying to save fields that don't exist in the database. This has been fixed by simplifying the player data structure.

### Error: "Could not find the 'gamer_tag' column"
**Solution**: Run the `create_minimal_players_table.sql` migration to ensure the players table has the correct basic structure.

### Players table doesn't exist
**Solution**: 
1. Check if table exists: Run `check_players_schema.sql`
2. If it doesn't exist: Run `create_minimal_players_table.sql`
3. Then proceed with other migrations

### Application shows "Failed to add player"
**Steps to debug**:
1. Check your Supabase logs for the exact error
2. Run `check_players_schema.sql` to see current table structure
3. Compare with what the application expects (name, jersey_number, position)
4. Run appropriate migration scripts

## Rollback (if needed)

To rollback this migration:

```sql
-- Remove constraints first
ALTER TABLE matches DROP CONSTRAINT IF EXISTS check_team1_player_goals_non_negative;
ALTER TABLE matches DROP CONSTRAINT IF EXISTS check_team2_player_goals_non_negative;
ALTER TABLE tournaments DROP CONSTRAINT IF EXISTS check_valid_scoring_system;

-- Drop index
DROP INDEX IF EXISTS idx_matches_player_goals;

-- Remove columns
ALTER TABLE matches DROP COLUMN IF EXISTS team1_player_goals;
ALTER TABLE matches DROP COLUMN IF EXISTS team2_player_goals;
ALTER TABLE tournaments DROP COLUMN IF EXISTS scoring_system;
```
