// Multi-Match System JavaScript for Team Tournaments

let subMatches = [];
let subMatchCounter = 0;

// Initialize multi-match system
function initializeMultiMatch() {
    const addButton = document.getElementById('addSubMatch');
    if (addButton) {
        addButton.addEventListener('click', addSubMatch);
    }
    
    // Load existing sub-matches if any
    // loadExistingSubMatches();
}

// Add a new sub-match
function addSubMatch() {
    subMatchCounter++;
    const subMatchId = `sub-match-${subMatchCounter}`;
    
    // Get the template from the page (set by the template engine)
    const subMatchTemplate = window.subMatchTemplate || '';
    const subMatchHtml = subMatchTemplate
        .replace(/{MATCH_ID}/g, subMatchId)
        .replace(/{MATCH_NUMBER}/g, subMatchCounter)
        .replace(/{COUNTER}/g, subMatchCounter);
    
    const container = document.getElementById('subMatchesContainer');
    container.insertAdjacentHTML('beforeend', subMatchHtml);
    
    // Add event listeners for the new sub-match
    const subMatchCard = container.lastElementChild;
    addSubMatchEventListeners(subMatchCard, subMatchId);
    
    // Update the sub-matches array
    subMatches.push({
        id: subMatchId,
        order: subMatchCounter,
        team1_player_id: '',
        team2_player_id: '',
        team1_goals: 0,
        team2_goals: 0,
        status: 'scheduled'
    });
    
    updateTeamSummary();
}

// Add event listeners to a sub-match card
function addSubMatchEventListeners(card, subMatchId) {
    // Remove button
    const removeBtn = card.querySelector('.remove-sub-match');
    removeBtn.addEventListener('click', () => removeSubMatch(subMatchId));
    
    // Goals inputs
    const team1GoalsInput = card.querySelector('.team1-goals-input');
    const team2GoalsInput = card.querySelector('.team2-goals-input');
    
    team1GoalsInput.addEventListener('input', () => updateSubMatchResult(subMatchId));
    team2GoalsInput.addEventListener('input', () => updateSubMatchResult(subMatchId));
    
    // Player selects
    const team1PlayerSelect = card.querySelector('.team1-player-select');
    const team2PlayerSelect = card.querySelector('.team2-player-select');
    
    team1PlayerSelect.addEventListener('change', () => {
        updateSubMatchResult(subMatchId);
        updatePlayerDropdowns(); // Ensure unique player selections
    });
    team2PlayerSelect.addEventListener('change', () => {
        updateSubMatchResult(subMatchId);
        updatePlayerDropdowns(); // Ensure unique player selections
    });
}

// Remove a sub-match
function removeSubMatch(subMatchId) {
    const card = document.querySelector(`[data-sub-match="${subMatchId}"]`);
    if (card) {
        card.remove();
        
        // Remove from array
        subMatches = subMatches.filter(sm => sm.id !== subMatchId);
        
        updateTeamSummary();
        updatePlayerDropdowns(); // Update dropdowns after removing a match
    }
}

// Update individual sub-match result
function updateSubMatchResult(subMatchId) {
    const card = document.querySelector(`[data-sub-match="${subMatchId}"]`);
    if (!card) return;
    
    const team1Goals = parseInt(card.querySelector('.team1-goals-input').value) || 0;
    const team2Goals = parseInt(card.querySelector('.team2-goals-input').value) || 0;
    const team1Player = card.querySelector('.team1-player-select').value;
    const team2Player = card.querySelector('.team2-player-select').value;
    
    const indicator = card.querySelector('.match-result-indicator');
    
    // Update the sub-match data
    const subMatch = subMatches.find(sm => sm.id === subMatchId);
    if (subMatch) {
        subMatch.team1_goals = team1Goals;
        subMatch.team2_goals = team2Goals;
        subMatch.team1_player_id = team1Player;
        subMatch.team2_player_id = team2Player;
    }
    
    // Get team names from page data attributes
    const team1Name = document.body.dataset.team1Name || 'Team 1';
    const team2Name = document.body.dataset.team2Name || 'Team 2';
    
    // Get selected player names
    const team1PlayerName = team1Player ? card.querySelector('.team1-player-select').options[card.querySelector('.team1-player-select').selectedIndex].text.split(' (')[0] : '';
    const team2PlayerName = team2Player ? card.querySelector('.team2-player-select').options[card.querySelector('.team2-player-select').selectedIndex].text.split(' (')[0] : '';
    
    // Update visual indicator
    if (team1Player && team2Player) {
        if (team1Goals > team2Goals) {
            indicator.className = 'match-result-indicator inline-flex items-center px-4 py-2 rounded-full text-sm font-bold bg-emerald-100 text-emerald-700';
            indicator.innerHTML = `<i class="fas fa-trophy mr-2"></i>${team1PlayerName} Wins!`;
        } else if (team2Goals > team1Goals) {
            indicator.className = 'match-result-indicator inline-flex items-center px-4 py-2 rounded-full text-sm font-bold bg-emerald-100 text-emerald-700';
            indicator.innerHTML = `<i class="fas fa-trophy mr-2"></i>${team2PlayerName} Wins!`;
        } else {
            // Equal goals (including 0-0) = Draw
            indicator.className = 'match-result-indicator inline-flex items-center px-4 py-2 rounded-full text-sm font-bold bg-yellow-100 text-yellow-700';
            indicator.innerHTML = '<i class="fas fa-handshake mr-2"></i>Draw!';
        }
    } else {
        indicator.className = 'match-result-indicator inline-flex items-center px-4 py-2 rounded-full text-sm font-bold bg-red-100 text-red-700';
        indicator.innerHTML = '<i class="fas fa-exclamation-triangle mr-2"></i>Select both players';
    }
    
    updateTeamSummary();
    updatePlayerDropdowns(); // Update all dropdowns to hide selected players
    updatePlayerParticipation(); // Update player participation status
    checkForKnockoutDraw(); // Check if tiebreaker needed
}

// Update team summary based on all sub-matches
function updateTeamSummary() {
    let team1Wins = 0;
    let team2Wins = 0;
    let draws = 0;
    let team1TotalGoals = 0;
    let team2TotalGoals = 0;
    
    // Calculate stats from all completed sub-matches
    subMatches.forEach(subMatch => {
        if (subMatch.team1_player_id && subMatch.team2_player_id) {
            team1TotalGoals += subMatch.team1_goals;
            team2TotalGoals += subMatch.team2_goals;
            
            if (subMatch.team1_goals > subMatch.team2_goals) {
                team1Wins++;
            } else if (subMatch.team2_goals > subMatch.team1_goals) {
                team2Wins++;
            } else {
                draws++;
            }
        }
    });
    
    // Get tournament data from page data attributes
    const scoringSystem = document.body.dataset.scoringSystem || 'win_based';
    const team1Name = document.body.dataset.team1Name || 'Team 1';
    const team2Name = document.body.dataset.team2Name || 'Team 2';
    
    // Calculate team scores based on scoring system
    let team1Score, team2Score;
    let scoreTypeLabel;
    
    if (scoringSystem === 'goal_based') {
        team1Score = team1TotalGoals;
        team2Score = team2TotalGoals;
        scoreTypeLabel = 'Goals';
    } else {
        // Win-based: 3 points per win, 1 point per draw
        team1Score = (team1Wins * 3) + draws;
        team2Score = (team2Wins * 3) + draws;
        scoreTypeLabel = 'Points';
    }
    
    // Update UI elements
    document.getElementById('team1Summary').textContent = team1Score;
    document.getElementById('team2Summary').textContent = team2Score;
    document.getElementById('team1SummaryType').textContent = scoreTypeLabel;
    document.getElementById('team2SummaryType').textContent = scoreTypeLabel;
    
    document.getElementById('totalMatches').textContent = subMatches.length;
    document.getElementById('totalGoals').textContent = `${team1TotalGoals} - ${team2TotalGoals}`;
    document.getElementById('drawCount').textContent = draws;
    
    // Overall outcome
    const overallOutcome = document.getElementById('overallOutcome');
    if (team1Score > team2Score) {
        overallOutcome.textContent = `${team1Name} Leads`;
        overallOutcome.className = 'text-sm text-emerald-600 mt-1 font-semibold';
    } else if (team2Score > team1Score) {
        overallOutcome.textContent = `${team2Name} Leads`;
        overallOutcome.className = 'text-sm text-emerald-600 mt-1 font-semibold';
    } else if (team1Score === team2Score && subMatches.length > 0) {
        overallOutcome.textContent = 'Tied';
        overallOutcome.className = 'text-sm text-yellow-600 mt-1 font-semibold';
    } else {
        overallOutcome.textContent = '-';
        overallOutcome.className = 'text-sm text-purple-600 mt-1 font-semibold';
    }
    
    // Update hidden form fields for submission
    document.getElementById('team1_score').value = team1Score;
    document.getElementById('team2_score').value = team2Score;
}

// Update all player dropdowns to hide already selected players
function updatePlayerDropdowns() {
    // Get all currently selected players
    const selectedTeam1Players = new Set();
    const selectedTeam2Players = new Set();
    
    document.querySelectorAll('.sub-match-card').forEach(card => {
        const team1Select = card.querySelector('.team1-player-select');
        const team2Select = card.querySelector('.team2-player-select');
        
        if (team1Select && team1Select.value) {
            selectedTeam1Players.add(team1Select.value);
        }
        if (team2Select && team2Select.value) {
            selectedTeam2Players.add(team2Select.value);
        }
    });
    
    // Update each dropdown to hide selected players (except current selection)
    document.querySelectorAll('.sub-match-card').forEach(card => {
        const team1Select = card.querySelector('.team1-player-select');
        const team2Select = card.querySelector('.team2-player-select');
        
        if (team1Select) {
            updateSelectOptions(team1Select, selectedTeam1Players);
        }
        
        if (team2Select) {
            updateSelectOptions(team2Select, selectedTeam2Players);
        }
    });
}

// Helper function to update select options by removing/adding them
function updateSelectOptions(selectElement, selectedPlayers) {
    const currentValue = selectElement.value;
    
    // Store original options if not already stored
    if (!selectElement._originalOptions) {
        selectElement._originalOptions = Array.from(selectElement.options).map(option => ({
            value: option.value,
            text: option.text,
            selected: option.selected
        }));
    }
    
    // Clear current options (except the empty one)
    const emptyOption = selectElement.querySelector('option[value=""]');
    selectElement.innerHTML = '';
    
    // Re-add empty option if it existed
    if (emptyOption) {
        selectElement.appendChild(emptyOption.cloneNode(true));
    }
    
    // Add back options that aren't selected elsewhere (or are currently selected)
    selectElement._originalOptions.forEach(optionData => {
        if (!optionData.value) return; // Skip empty options
        
        // Show option if:
        // 1. It's the currently selected value, OR
        // 2. It's not selected in any other dropdown
        const shouldShow = (optionData.value === currentValue) || !selectedPlayers.has(optionData.value);
        
        if (shouldShow) {
            const option = document.createElement('option');
            option.value = optionData.value;
            option.text = optionData.text;
            option.selected = optionData.value === currentValue;
            selectElement.appendChild(option);
        }
    });
}

// Player Participation Tracking
// Track which players are playing vs substitutes
function updatePlayerParticipation() {
    const team1PlayersPlaying = new Set();
    const team2PlayersPlaying = new Set();
    
    // Get all players currently playing in sub-matches
    document.querySelectorAll('.sub-match-card').forEach(card => {
        const team1Select = card.querySelector('.team1-player-select');
        const team2Select = card.querySelector('.team2-player-select');
        
        if (team1Select && team1Select.value) {
            team1PlayersPlaying.add(team1Select.value);
        }
        if (team2Select && team2Select.value) {
            team2PlayersPlaying.add(team2Select.value);
        }
    });
    
    // Update participation status for each player
    document.querySelectorAll('.player-participation-item').forEach(item => {
        const playerId = item.dataset.playerId;
        const team = item.dataset.team;
        const statusElement = item.querySelector('.participation-status');
        const statusText = item.querySelector('.status-text');
        const statusIcon = item.querySelector('i');
        
        const isPlaying = (team === '1' && team1PlayersPlaying.has(playerId)) || 
                         (team === '2' && team2PlayersPlaying.has(playerId));
        
        if (isPlaying) {
            statusText.textContent = 'Playing';
            statusText.className = 'status-text text-green-600 font-semibold';
            statusIcon.className = 'fas fa-play-circle text-green-500 ml-1';
            item.className = item.className.replace('bg-gray-50', 'bg-green-50 border-green-200');
        } else {
            statusText.textContent = 'Substitute';
            statusText.className = 'status-text text-orange-600 font-semibold';
            statusIcon.className = 'fas fa-exclamation-circle text-orange-500 ml-1';
            item.className = item.className.replace('bg-green-50 border-green-200', 'bg-gray-50');
        }
    });
    
    // Update participation counts
    const team1Playing = team1PlayersPlaying.size;
    const team2Playing = team2PlayersPlaying.size;
    
    const totalTeam1Players = document.querySelectorAll('[data-team="1"].player-participation-item').length;
    const totalTeam2Players = document.querySelectorAll('[data-team="2"].player-participation-item').length;
    
    document.getElementById('team1PlayingCount').textContent = team1Playing;
    document.getElementById('team1SubstituteCount').textContent = totalTeam1Players - team1Playing;
    document.getElementById('team2PlayingCount').textContent = team2Playing;
    document.getElementById('team2SubstituteCount').textContent = totalTeam2Players - team2Playing;
    
    // Show warning if no players are playing
    updateParticipationWarning(team1Playing + team2Playing);
}

// Show/hide participation warning
function updateParticipationWarning(totalPlaying) {
    let warningElement = document.getElementById('participationWarning');
    
    if (totalPlaying === 0) {
        if (!warningElement) {
            warningElement = document.createElement('div');
            warningElement.id = 'participationWarning';
            warningElement.className = 'mt-4 p-4 bg-yellow-100 border border-yellow-300 rounded-lg text-center';
            warningElement.innerHTML = `
                <div class="flex items-center justify-center text-yellow-800">
                    <i class="fas fa-exclamation-triangle mr-2"></i>
                    <span class="font-semibold">No players selected to play! Please add player matches to assign playing roles.</span>
                </div>
            `;
            document.getElementById('playerParticipation').appendChild(warningElement);
        }
    } else {
        if (warningElement) {
            warningElement.remove();
        }
    }
}

// Check for knockout draw and show tiebreaker options
function checkForKnockoutDraw() {
    // Get tournament format from page data
    const tournamentFormat = document.body.dataset.tournamentFormat || 'league';
    
    if (tournamentFormat !== 'knockout') {
        return; // Only applies to knockout tournaments
    }
    
    const team1Score = parseInt(document.getElementById('team1_score').value) || 0;
    const team2Score = parseInt(document.getElementById('team2_score').value) || 0;
    
    let tiebreakerElement = document.getElementById('tiebreakerOptions');
    
    // Show tiebreaker options if it's a draw
    if (team1Score === team2Score && team1Score > 0) {
        if (!tiebreakerElement) {
            tiebreakerElement = document.createElement('div');
            tiebreakerElement.id = 'tiebreakerOptions';
            tiebreakerElement.className = 'mt-6 p-6 bg-yellow-50 border-2 border-yellow-300 rounded-2xl';
            tiebreakerElement.innerHTML = `
                <div class="text-center mb-4">
                    <h4 class="text-lg font-bold text-yellow-800 mb-2">
                        <i class="fas fa-balance-scale mr-2"></i>Knockout Draw Detected
                    </h4>
                    <p class="text-yellow-700">This match ended in a draw. Choose a tiebreaker format:</p>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <button type="button" id="bestOf1Tiebreaker" class="tiebreaker-option p-4 border-2 border-yellow-300 rounded-xl bg-white hover:bg-yellow-50 transition-all">
                        <div class="text-center">
                            <i class="fas fa-bolt text-yellow-600 text-2xl mb-2"></i>
                            <h5 class="font-bold text-yellow-800 mb-1">Best of 1</h5>
                            <p class="text-sm text-yellow-600">Single decisive match</p>
                        </div>
                    </button>
                    
                    <button type="button" id="bestOf3Tiebreaker" class="tiebreaker-option p-4 border-2 border-yellow-300 rounded-xl bg-white hover:bg-yellow-50 transition-all">
                        <div class="text-center">
                            <i class="fas fa-trophy text-yellow-600 text-2xl mb-2"></i>
                            <h5 class="font-bold text-yellow-800 mb-1">Best of 3</h5>
                            <p class="text-sm text-yellow-600">First to win 2 matches</p>
                        </div>
                    </button>
                </div>
                
                <div class="mt-4 p-3 bg-yellow-100 rounded-lg text-center">
                    <p class="text-sm text-yellow-700">
                        <i class="fas fa-info-circle mr-1"></i>
                        Tiebreaker matches will be created automatically after you save this result.
                    </p>
                </div>
                
                <input type="hidden" name="tiebreaker_type" id="tiebreakerType" value="">
            `;
            
            // Insert after team summary
            const teamSummary = document.getElementById('teamSummary');
            teamSummary.insertAdjacentElement('afterend', tiebreakerElement);
            
            // Add event listeners for tiebreaker options
            document.getElementById('bestOf1Tiebreaker').addEventListener('click', () => selectTiebreakerType('best_of_1'));
            document.getElementById('bestOf3Tiebreaker').addEventListener('click', () => selectTiebreakerType('best_of_3'));
        }
    } else {
        // Remove tiebreaker options if not a draw
        if (tiebreakerElement) {
            tiebreakerElement.remove();
        }
    }
}

// Select tiebreaker type
function selectTiebreakerType(type) {
    document.getElementById('tiebreakerType').value = type;
    
    // Update UI to show selection
    document.querySelectorAll('.tiebreaker-option').forEach(option => {
        option.classList.remove('border-yellow-500', 'bg-yellow-100');
        option.classList.add('border-yellow-300', 'bg-white');
    });
    
    const selectedOption = document.getElementById(type === 'best_of_1' ? 'bestOf1Tiebreaker' : 'bestOf3Tiebreaker');
    selectedOption.classList.remove('border-yellow-300', 'bg-white');
    selectedOption.classList.add('border-yellow-500', 'bg-yellow-100');
}

// Load existing sub-matches from server data
function loadExistingSubMatches() {
    // Check if there are existing sub-matches passed from the server
    if (window.existingSubMatches && window.existingSubMatches.length > 0) {
        console.log('Loading existing sub-matches:', window.existingSubMatches);
        
        // Clear any default sub-matches that might have been added
        const container = document.getElementById('subMatchesContainer');
        container.innerHTML = '';
        subMatches = [];
        subMatchCounter = 0;
        
        // Load each existing sub-match
        window.existingSubMatches.forEach((existingMatch, index) => {
            addSubMatchWithData(existingMatch, index + 1);
        });
        
        // Update displays
        updateTeamSummary();
        updatePlayerDropdowns();
        updatePlayerParticipation();
        checkForKnockoutDraw();
    } else {
        // Add at least one empty sub-match to start
        addSubMatch();
    }
}

// Add a sub-match with existing data
function addSubMatchWithData(matchData, matchNumber) {
    subMatchCounter = matchNumber;
    const subMatchId = `sub-match-${subMatchCounter}`;
    
    // Get the template and replace placeholders
    const subMatchTemplate = window.subMatchTemplate || '';
    const subMatchHtml = subMatchTemplate
        .replace(/{MATCH_ID}/g, subMatchId)
        .replace(/{MATCH_NUMBER}/g, matchNumber)
        .replace(/{COUNTER}/g, subMatchCounter);
    
    const container = document.getElementById('subMatchesContainer');
    container.insertAdjacentHTML('beforeend', subMatchHtml);
    
    // Get the newly added sub-match card
    const subMatchCard = container.lastElementChild;
    
    // Populate with existing data
    const team1PlayerSelect = subMatchCard.querySelector('.team1-player-select');
    const team2PlayerSelect = subMatchCard.querySelector('.team2-player-select');
    const team1GoalsInput = subMatchCard.querySelector('.team1-goals-input');
    const team2GoalsInput = subMatchCard.querySelector('.team2-goals-input');
    
    // Set player selections (with safety check for existing options)
    if (team1PlayerSelect && matchData.team1_player_id) {
        const team1Option = team1PlayerSelect.querySelector(`option[value="${matchData.team1_player_id}"]`);
        if (team1Option) {
            team1PlayerSelect.value = matchData.team1_player_id;
        } else {
            console.warn(`Team 1 player ${matchData.team1_player_id} not found in options`);
        }
    }
    
    if (team2PlayerSelect && matchData.team2_player_id) {
        const team2Option = team2PlayerSelect.querySelector(`option[value="${matchData.team2_player_id}"]`);
        if (team2Option) {
            team2PlayerSelect.value = matchData.team2_player_id;
        } else {
            console.warn(`Team 2 player ${matchData.team2_player_id} not found in options`);
        }
    }
    
    // Set goal values
    if (team1GoalsInput) team1GoalsInput.value = matchData.team1_player_goals || 0;
    if (team2GoalsInput) team2GoalsInput.value = matchData.team2_player_goals || 0;
    
    // Add event listeners
    addSubMatchEventListeners(subMatchCard, subMatchId);
    
    // Add to subMatches array
    subMatches.push({
        id: subMatchId,
        order: subMatchCounter,
        team1_player_id: matchData.team1_player_id || '',
        team2_player_id: matchData.team2_player_id || '',
        team1_goals: matchData.team1_player_goals || 0,
        team2_goals: matchData.team2_player_goals || 0,
        status: 'completed'
    });
    
    // Update the sub-match result display
    updateSubMatchResult(subMatchId);
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('multiMatchSection')) {
        initializeMultiMatch();
        
        // Load existing sub-matches or add a new one
        loadExistingSubMatches();
        
        // Initialize player dropdown constraints and participation tracking
        updatePlayerDropdowns();
        updatePlayerParticipation();
    }
});
