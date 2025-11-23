# Octavia Web - Installation & Setup Guide

This guide provides step-by-step instructions to install all required packages and set up the Octavia Web application.

---

## Prerequisites

Before installing Octavia Web, ensure you have the following installed:

### Required Software
- **Node.js**: v18.0.0 or higher ([Download](https://nodejs.org/))
- **npm**: v9.0.0 or higher (comes with Node.js)
- **Git**: v2.30.0 or higher ([Download](https://git-scm.com/))

### Verify Installation
```bash
node --version    # Should output v18.x.x or higher
npm --version     # Should output v9.x.x or higher
git --version     # Should output v2.x.x or higher
```

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/LunarTechAI/octavia.git
cd octavia/octavia-web
```

### 2. Install All Packages (Single Command)

```bash
npm install
```

This command will automatically install all production and development dependencies listed below.

### 3. Run Development Server

```bash
npm run dev
```

The application will be available at **http://localhost:3000**

---

## Package List

### Production Dependencies

All packages required for the application to run in production:

| Package | Version | Purpose |
|---------|---------|---------|
| `next` | 16.0.3 | Next.js framework (React with SSR/SSG) |
| `react` | 19.2.0 | React library for UI components |
| `react-dom` | 19.2.0 | React DOM rendering |
| `framer-motion` | ^12.23.24 | Animation library for smooth transitions |
| `lucide-react` | ^0.554.0 | Icon library with 1000+ icons |
| `clsx` | ^2.1.1 | Utility for conditional className strings |
| `tailwind-merge` | ^3.4.0 | Merge Tailwind CSS classes without conflicts |
| `class-variance-authority` | ^0.7.1 | Type-safe component variants |

**Install command (if needed separately):**
```bash
npm install next@16.0.3 react@19.2.0 react-dom@19.2.0 framer-motion@^12.23.24 lucide-react@^0.554.0 clsx@^2.1.1 tailwind-merge@^3.4.0 class-variance-authority@^0.7.1
```

### Development Dependencies

Packages required only for development and build processes:

| Package | Version | Purpose |
|---------|---------|---------|
| `typescript` | ^5 | TypeScript language support |
| `@types/node` | ^20 | TypeScript types for Node.js |
| `@types/react` | ^19 | TypeScript types for React |
| `@types/react-dom` | ^19 | TypeScript types for React DOM |
| `tailwindcss` | ^4 | Utility-first CSS framework |
| `@tailwindcss/postcss` | ^4 | PostCSS plugin for Tailwind v4 |
| `tw-animate-css` | ^1.4.0 | Animation utilities for Tailwind |
| `eslint` | ^9 | JavaScript/TypeScript linter |
| `eslint-config-next` | 16.0.3 | Next.js ESLint configuration |
| `babel-plugin-react-compiler` | 1.0.0 | React Compiler for optimization |

**Install command (if needed separately):**
```bash
npm install -D typescript@^5 @types/node@^20 @types/react@^19 @types/react-dom@^19 tailwindcss@^4 @tailwindcss/postcss@^4 tw-animate-css@^1.4.0 eslint@^9 eslint-config-next@16.0.3 babel-plugin-react-compiler@1.0.0
```

---

## Complete Installation Commands

### Option 1: Automatic Installation (Recommended)

```bash
# Clone repository
git clone https://github.com/LunarTechAI/octavia.git

# Navigate to project
cd octavia/octavia-web

# Install all dependencies
npm install

# Start development server
npm run dev
```

### Option 2: Manual Installation

If you need to install packages individually:

```bash
# Install production dependencies
npm install next@16.0.3 react@19.2.0 react-dom@19.2.0
npm install framer-motion@^12.23.24
npm install lucide-react@^0.554.0
npm install clsx@^2.1.1 tailwind-merge@^3.4.0 class-variance-authority@^0.7.1

# Install development dependencies
npm install -D typescript@^5 @types/node@^20 @types/react@^19 @types/react-dom@^19
npm install -D tailwindcss@^4 @tailwindcss/postcss@^4 tw-animate-css@^1.4.0
npm install -D eslint@^9 eslint-config-next@16.0.3
npm install -D babel-plugin-react-compiler@1.0.0
```

---

## Environment Setup

### 1. Create Environment File

Create a `.env.local` file in the `octavia-web` directory:

```bash
touch .env.local
```

### 2. Add Environment Variables

```env
# Application URL
NEXT_PUBLIC_APP_URL=http://localhost:3000

# API Configuration (for future use)
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_API_KEY=

# Analytics (optional)
NEXT_PUBLIC_GA_ID=
```

---

## Available Scripts

After installation, you can run these commands:

### Development

```bash
npm run dev
```
Starts the development server with hot-reload at http://localhost:3000

### Production Build

```bash
npm run build
```
Creates an optimized production build

### Production Server

```bash
npm run start
```
Runs the production build (must run `npm run build` first)

### Linting

```bash
npm run lint
```
Runs ESLint to check code quality

---

## Verification

After installation, verify everything works:

### 1. Check Dependencies

```bash
npm list --depth=0
```

Expected output:
```
octavia-web@0.1.0
├── class-variance-authority@0.7.1
├── clsx@2.1.1
├── framer-motion@12.23.24
├── lucide-react@0.554.0
├── next@16.0.3
├── react@19.2.0
├── react-dom@19.2.0
└── tailwind-merge@3.4.0
```

### 2. Start Development Server

```bash
npm run dev
```

You should see:
```
▲ Next.js 16.0.3 (Turbopack)
- Local:         http://localhost:3000
- Network:       http://192.168.x.x:3000

✓ Starting...
✓ Ready in 424ms
```

### 3. Build for Production

```bash
npm run build
```

Expected output:
```
✓ Finalizing page optimization
Route (app)                              Size
┌ ○ /                                    1.2 kB
├ ○ /dashboard                           ...
...
○  (Static)  prerendered as static content
```

---

## Troubleshooting

### Issue: `npm install` fails

**Solution:**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall
npm install
```

### Issue: Port 3000 already in use

**Solution:**
```bash
# Use a different port
PORT=3001 npm run dev

# Or kill the process using port 3000
lsof -ti:3000 | xargs kill -9
```

### Issue: TypeScript errors

**Solution:**
```bash
# Ensure TypeScript is installed
npm install -D typescript@^5

# Restart your IDE/editor
```

### Issue: Module not found errors

**Solution:**
```bash
# Reinstall dependencies
npm install

# Clear Next.js cache
rm -rf .next
npm run dev
```

---

## Additional Tools (Optional)

### Recommended IDE Extensions

For **VS Code**:
- ESLint
- Tailwind CSS IntelliSense
- TypeScript and JavaScript Language Features
- Prettier (optional)

### Install Prettier (Optional)

```bash
npm install -D prettier eslint-config-prettier
```

Create `.prettierrc`:
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": false,
  "tabWidth": 4,
  "printWidth": 100
}
```

---

## Docker Setup (Alternative)

### Dockerfile

Create a `Dockerfile` in `octavia-web/`:

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
```

### Build and Run

```bash
docker build -t octavia-web .
docker run -p 3000:3000 octavia-web
```

---

## System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| Node.js | v18.0 | v20.0+ |
| RAM | 8 GB | 16 GB |
| Disk Space | 500 MB | 2 GB |
| CPU | 2 cores | 4+ cores |
| OS | macOS 11+, Ubuntu 20.04+, Windows 10+ | Latest stable |

---

## Next Steps

After successful installation:

1. ✅ **Explore the application**: Navigate to http://localhost:3000
2. ✅ **Check all routes**: Visit all dashboard pages to ensure they load
3. ✅ **Review documentation**: Read `REQUIREMENTS.md` and `dashboard_pages_map.md`
4. ✅ **Start developing**: Make changes and see them hot-reload instantly

---

## Support

### Documentation
- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Framer Motion Documentation](https://www.framer.com/motion/)

### Issues
If you encounter any issues, please:
1. Check this installation guide
2. Search existing GitHub issues
3. Create a new issue with detailed error logs

---

**Last Updated**: 2025-11-23  
**Version**: 1.0.0  
**Status**: ✅ Ready for Development
