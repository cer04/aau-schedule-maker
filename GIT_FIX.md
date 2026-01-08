# Quick Fix for Git Errors

Run these commands one by one:

# 1. Set your Git identity (replace with your info)
git config --global user.email "your-email@example.com"
git config --global user.name "Your Name"

# 2. Remove the old remote (since it already exists)
git remote remove origin

# 3. Create the GitHub repo first, then add the correct remote
# Replace YOUR-USERNAME with your actual GitHub username
git remote add origin https://github.com/YOUR-USERNAME/aau-schedule-maker.git

# 4. Make the commit (if not already done)
git add .
git commit -m "Initial commit"

# 5. Push to GitHub
git push -u origin main

---

## Important: Before Step 3, you need to:
1. Go to https://github.com/new
2. Create a repository named: `aau-schedule-maker`
3. Don't initialize with README
4. Click "Create repository"
5. Copy the URL GitHub shows you
6. Use that URL in the `git remote add origin` command

## Or use the GitHub Desktop app (easier):
1. Download GitHub Desktop: https://desktop.github.com/
2. Open it and sign in
3. File → Add Local Repository → Choose your folder
4. It will ask to create a repo - click yes
5. Click "Publish repository"
6. Done! Much easier.
