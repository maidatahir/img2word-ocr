
$commits = git log --format="%H" --reverse
$totalCommits = $commits.Count
$startDate = [datetime]"2026-04-21 09:30:00"
$endDate = [datetime]"2026-05-02 17:45:00"
$totalSeconds = ($endDate - $startDate).TotalSeconds
$interval = $totalSeconds / ($totalCommits + 1)

# Create a temporary branch from the first commit's parent (empty state if needed)
git checkout --orphan backdated_temp
git rm -rf .

for ($i = 0; $i -lt $totalCommits; $i++) {
    $commitHash = $commits[$i]
    $newDate = $startDate.AddSeconds($i * $interval).ToString("yyyy-MM-ddTHH:mm:ss")
    
    # Set environment variables for the date
    $env:GIT_AUTHOR_DATE = "$newDate"
    $env:GIT_COMMITTER_DATE = "$newDate"
    
    # Cherry pick the commit content
    git cherry-pick $commitHash --no-commit
    $msg = git log --format=%B -n 1 $commitHash
    git commit -m "$msg" --date "$newDate"
}

# Swap branches
git checkout main
git reset --hard backdated_temp
git branch -D backdated_temp
