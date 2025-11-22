# 🚀 Development Workflow Guide

## 📋 Branch Strategy

### **main Branch**
- **Purpose**: Production-ready, stable deployments
- **Status**: Protected - no direct pushes except major releases
- **Deployment**: Triggers Render.com production deployment
- **Current State**: Basic trading charts with sharing functionality (stable)

### **dev Branch**
- **Purpose**: Development and experimental features
- **Status**: Active development branch with latest enhancements
- **Deployment**: Can be deployed to staging/preview environments
- **Current State**: Enhanced UX with professional interface

## 🔄 Development Process

### **Daily Development Workflow**
```bash
# 1. Always work on dev branch
git checkout dev

# 2. Make your changes locally
# Edit files, test, iterate

# 3. Commit to dev branch
git add .
git commit -m "feat: your feature description"

# 4. Push to dev for testing
git push origin dev
```

### **When to Merge to Main**
- ✅ **Major feature completions** (new chart types, major UI changes)
- ✅ **Bug fixes for production issues**
- ✅ **Performance improvements**
- ✅ **Security updates**
- ❌ **Small UI tweaks** (keep in dev)
- ❌ **Experimental features** (test in dev first)

### **Merging to Main Process**
```bash
# 1. Switch to main
git checkout main

# 2. Merge dev into main
git merge dev

# 3. Test locally one more time
python3 api/index.py

# 4. Push to main (triggers deployment)
git push origin main
```

## 🎯 Deployment Strategy

### **Production (main branch)**
- **Target**: Render.com production
- **Triggers**: Push to `main` branch
- **Environment**: Production database, live market data
- **Status**: Stable, public-facing

### **Development (dev branch)**
- **Target**: Staging/preview or local testing
- **Triggers**: Push to `dev` branch
- **Environment**: Development mode, can use mock data
- **Status**: Experimental, testing

### **Feature Branches** (Optional)
```bash
# Create feature branch from dev
git checkout -b feature/amazing-charts

# Work on feature
# ... make changes ...

# Merge back to dev
git checkout dev
git merge feature/amazing-charts
git push origin dev
```

## 🛡️ Branch Protection Rules

### **Main Branch Rules**
- **Require PR**: All changes must come through dev → main PR
- **CI/CD**: Automated tests must pass
- **Code Review**: At least one review required for major changes
- **Deployment**: Automatic only on successful merge

### **Dev Branch Rules**
- **Direct Push**: Allowed for rapid development
- **Testing**: Must pass basic functionality tests
- **Code Quality**: Maintain code standards
- **Backup**: Push regularly to avoid loss

## 📱 Preview/Testing

### **Dev Branch Testing**
- **URL**: Your dev deployment (if configured)
- **Local**: `python3 api/index.py` → http://localhost:5001
- **Features**: Latest enhancements, experimental UI

### **Production Testing**
- **URL**: Your production deployment
- **Features**: Stable, thoroughly tested functionality
- **Status**: Public-facing, must be reliable

## 🔄 Typical Workflow Example

### **Adding New Feature**
1. **Develop on dev**: `git checkout dev` → make changes → `git push origin dev`
2. **Test Feature**: Verify functionality in dev environment
3. **Iterate**: Make refinements based on testing
4. **Prepare for Production**: Ensure feature is stable and documented
5. **Merge to Main**: `git checkout main` → `git merge dev` → `git push origin main`
6. **Monitor**: Verify production deployment works correctly

### **Bug Fix for Production**
1. **Fix on dev**: Implement fix on dev branch
2. **Test**: Verify fix resolves issue
3. **Hotfix**: Merge to main immediately if critical
4. **Deploy**: Push to main for instant production fix

## 🎨 Current Branch States

### **main** (Production - v1.0)
```
✅ Basic MNQ Futures Charts
✅ Multi-timeframe analysis (30s, 5m, 15m)
✅ Opening range calculations
✅ Share & embed functionality
✅ yfinance data integration
✅ Render.com deployment ready
```

### **dev** (Development - v1.1)
```
✅ All main features
✅ Professional welcome state
✅ Enhanced toggle effects
✅ Progressive chart reveal
✅ Advanced loading states
✅ Hover-only glow effects
🚧 Next: [current development focus]
```

## 📝 Commit Message Guidelines

### **Dev Branch Commits**
```bash
feat: add enhanced toggle animations
fix: resolve chart rendering issue
refactor: improve toggle state management
docs: update API documentation
chore: improve code formatting
```

### **Main Branch Commits**
```bash
feat: launch production trading charts v1.0
fix: critical deployment issue
perf: improve chart loading performance
security: update dependencies
release: version 1.1.0 with UX improvements
```

## ⚠️ Important Notes

- **Never** force push to main unless absolutely necessary
- **Always** test changes locally before pushing to dev
- **Keep** dev branch deployable and functional
- **Backup** your work regularly by pushing to dev
- **Communicate** when planning major main branch updates

This workflow ensures stable production deployments while enabling rapid development and experimentation!