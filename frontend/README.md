# Scholarship Portal Frontend

A comprehensive React.js frontend application for the Scholarship Portal system that consumes Django REST APIs.

## Features

- **Multi-role Authentication**: Student, Institute Admin, Department Admin, Finance Admin, Super Admin
- **Role-based Dashboards**: Customized interfaces for each user role
- **Scholarship Management**: Application submission, tracking, and management
- **Finance Module**: Scholarship calculation, payment management, and DBT transfers
- **Responsive Design**: Mobile-friendly interface using Material-UI
- **JWT Authentication**: Secure token-based authentication with auto-refresh

## Technology Stack

- **React.js 18.2.0**: Modern React with hooks and functional components
- **Material-UI (MUI)**: Professional UI component library
- **React Router DOM**: Client-side routing with role-based redirects
- **Axios**: HTTP client for API communication
- **Zustand**: Lightweight state management
- **React Query**: Server state management and caching
- **JWT Decode**: Token parsing and validation

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── LoadingSpinner.js
│   │   ├── Navigation.js
│   │   ├── ProtectedRoute.js
│   │   └── RoleBasedRedirect.js
│   ├── pages/
│   │   ├── auth/
│   │   │   ├── LoginPage.js
│   │   │   └── RegisterPage.js
│   │   ├── student/
│   │   │   ├── StudentDashboard.js
│   │   │   ├── StudentApplications.js
│   │   │   └── StudentProfile.js
│   │   ├── institute/
│   │   │   ├── InstituteDashboard.js
│   │   │   ├── InstituteApplications.js
│   │   │   └── InstituteReports.js
│   │   ├── department/
│   │   │   ├── DepartmentDashboard.js
│   │   │   ├── DepartmentApplications.js
│   │   │   └── DepartmentReports.js
│   │   ├── finance/
│   │   │   ├── FinanceDashboard.js
│   │   │   ├── FinanceApplications.js
│   │   │   └── FinanceReports.js
│   │   ├── admin/
│   │   │   └── AdminDashboard.js
│   │   └── NotFoundPage.js
│   ├── services/
│   │   └── api.js
│   ├── store/
│   │   └── authStore.js
│   ├── App.js
│   └── index.js
└── package.json
```

## Installation & Setup

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- Django backend API running on http://localhost:8000

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The application will be available at `http://localhost:3000`

## Configuration

### API Configuration

The API base URL is configured in `src/services/api.js`. By default, it points to:
```javascript
const API_BASE_URL = 'http://localhost:8000/api'
```

Update this URL if your Django backend is running on a different port or domain.

### Authentication

The application uses JWT tokens for authentication:
- Access tokens are stored in localStorage
- Automatic token refresh on API calls
- Role-based route protection
- Automatic logout on token expiration

## Available Scripts

- `npm start`: Runs the app in development mode
- `npm build`: Builds the app for production
- `npm test`: Runs the test suite
- `npm run lint`: Runs ESLint for code quality

## User Roles & Routes

### Student Routes
- `/student/dashboard`: Main dashboard with application overview
- `/student/applications`: Submit and manage scholarship applications
- `/student/profile`: Update personal information

### Institute Admin Routes
- `/institute/dashboard`: Institute overview and stats
- `/institute/applications`: Verify student applications
- `/institute/reports`: Generate institute reports

### Department Admin Routes
- `/department/dashboard`: Department overview
- `/department/applications`: Manage department applications
- `/department/reports`: Department analytics

### Finance Admin Routes
- `/finance/dashboard`: **Main finance operations**
  - Calculate scholarship amounts
  - Update payment status
  - Initiate DBT transfers
- `/finance/applications`: Detailed application management
- `/finance/reports`: Financial reports and analytics

### Super Admin Routes
- `/admin/dashboard`: System administration

## Key Features

### Finance Dashboard (Primary Feature)

The Finance Dashboard (`/finance/dashboard`) is the core component that implements all the requested finance module features:

1. **Scholarship Calculation**:
   - Calculate tuition fees, maintenance allowance, and other allowances
   - Automatic total calculation
   - Save calculated amounts to database

2. **Payment Status Management**:
   - Mark tuition fees as paid
   - Mark maintenance allowance as paid
   - Update payment status with remarks
   - Track payment history

3. **DBT Transfer Simulation**:
   - Simulate Direct Benefit Transfer to student bank accounts
   - Validate bank details before transfer
   - Track transfer status and history

4. **Finance Reports**:
   - Dashboard with key financial metrics
   - Application statistics
   - Payment tracking
   - Transfer summaries

### Authentication Features

- **Multi-role Login**: Different dashboards based on user role
- **JWT Token Management**: Automatic refresh and validation
- **Role-based Access Control**: Protected routes for each user type
- **Persistent Sessions**: Maintain login state across browser sessions

## Demo Credentials

The application includes demo credentials for testing:

- **Student**: student@demo.com / password123
- **Institute Admin**: institute@demo.com / password123
- **Department Admin**: department@demo.com / password123
- **Finance Admin**: finance@demo.com / password123
- **Super Admin**: admin@demo.com / password123

## API Integration

The frontend integrates with the Django REST API through these main endpoints:

### Authentication
- `POST /api/auth/login/`: User login
- `POST /api/auth/register/`: User registration
- `POST /api/auth/logout/`: User logout
- `GET /api/auth/user/`: Get current user

### Student Operations
- `GET /api/students/applications/`: Get student applications
- `POST /api/students/applications/`: Create new application
- `PUT /api/students/applications/{id}/`: Update application
- `GET /api/students/profile/`: Get student profile
- `PUT /api/students/profile/`: Update student profile

### Finance Operations
- `GET /api/finance/dashboard/`: Get finance dashboard data
- `GET /api/finance/pending-applications/`: Get applications needing finance action
- `POST /api/finance/calculate-scholarship/{id}/`: Calculate scholarship amount
- `POST /api/finance/update-payment-status/{id}/`: Update payment status
- `POST /api/finance/dbt-transfer/{id}/`: Simulate DBT transfer
- `GET /api/finance/reports/`: Generate finance reports

## Development Notes

### State Management

The application uses Zustand for state management:
- `authStore.js`: Handles authentication state, login/logout, and user data
- Automatic persistence of authentication state
- Role-based helper functions

### Error Handling

- Comprehensive error handling for API calls
- User-friendly error messages using Notistack
- Automatic retry for failed requests
- Loading states for better UX

### Responsive Design

- Mobile-first design approach
- Responsive navigation with drawer for mobile devices
- Adaptive layouts using Material-UI Grid system
- Touch-friendly interfaces

## Production Deployment

1. Build the application:
```bash
npm run build
```

2. The `build` folder contains the production-ready files
3. Deploy to your preferred hosting service (Netlify, Vercel, AWS, etc.)
4. Update the API base URL for production environment

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

1. Follow the existing code structure and naming conventions
2. Use Material-UI components for consistency
3. Implement proper error handling for all API calls
4. Add loading states for better user experience
5. Ensure responsive design for all new components

## Support

For technical support or questions about the frontend implementation, please refer to:
- Component documentation in the source code
- Material-UI documentation: https://mui.com/
- React documentation: https://react.dev/
- React Query documentation: https://tanstack.com/query/latest
