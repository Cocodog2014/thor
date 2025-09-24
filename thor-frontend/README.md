# Thor Frontend - React + Vite

A modern React frontend built with Vite and TypeScript for the Thor Norse mythology application. Features a dark theme with Norse-inspired design and comprehensive CRUD operations for Heroes, Quests, and Artifacts.

## 🚀 Features

- **Modern Stack**: React 19 + Vite + TypeScript
- **UI Framework**: Material-UI (MUI) with custom Thor theme
- **State Management**: TanStack React Query for server state
- **Routing**: React Router for SPA navigation
- **Forms**: React Hook Form with Yup validation
- **API Integration**: Axios for HTTP requests to Django backend
- **Real-time Updates**: Optimistic updates and automatic refetching
- **Responsive Design**: Mobile-first responsive layout
- **Toast Notifications**: User feedback with react-hot-toast

## 🎨 Design Theme

- **Dark Theme**: Norse mythology inspired dark color scheme
- **Colors**: 
  - Primary: Thor Blue (#1976d2)
  - Secondary: Lightning Red (#f50057)
  - Background: Deep space (#0a0e13, #1a1f2e)
- **Typography**: Cinzel serif font for headings (Norse runic style)
- **Icons**: Material-UI icons representing heroes, quests, and artifacts

## 🛠️ Setup Instructions

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Django backend running on `http://127.0.0.1:8000`

### Installation

1. **Navigate to frontend directory:**
   ```bash
   cd thor-frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Open in browser:**
   - Frontend: `http://localhost:5173`
   - Make sure Django backend is running on `http://127.0.0.1:8000`

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## 🔧 Configuration

### API Configuration
The frontend is configured to connect to the Django backend at:
```typescript
baseURL: 'http://127.0.0.1:8000/api'
```

Update `src/services/api.ts` if your backend runs on a different URL.

## 📱 Current Status

✅ **Completed:**
- Project setup with Vite + React + TypeScript
- Material-UI dark theme with Thor styling
- React Router navigation setup
- API services and React Query hooks
- Dashboard with statistics display
- Responsive layout with sidebar navigation

🚧 **In Development:**
- Heroes management page (CRUD operations)
- Quests management page (CRUD operations)  
- Artifacts management page (CRUD operations)
- Form components for data entry
- Data tables with filtering and sorting

## 🎯 API Integration

The frontend integrates with the Django REST API endpoints:

- `GET /api/` - API overview
- `GET /api/stats/` - Application statistics
- `GET /api/heroes/` - List heroes
- `POST /api/heroes/` - Create hero
- `GET /api/heroes/{id}/` - Hero details
- Similar endpoints for quests and artifacts

## 🔄 State Management

Uses TanStack React Query for:
- **Caching**: Intelligent caching of API responses
- **Optimistic Updates**: Immediate UI updates
- **Background Refetching**: Automatic data synchronization
- **Error Handling**: Comprehensive error states
- **Loading States**: Built-in loading indicators

## 🚀 Development

### Hot Module Replacement
Vite provides instant hot reloading for rapid development.

### TypeScript
Strict TypeScript configuration with full type safety.

## 🔗 Backend Integration

Ensure the Django backend is running with CORS configured for:
- `http://localhost:5173` (Vite dev server)
- `http://127.0.0.1:5173`

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
