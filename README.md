# Personal Expense Tracker with AI Assistant

A comprehensive expense tracking application built with Streamlit, featuring complete user management, interactive dashboards, expense management, and AI-powered financial insights using CrewAI agents.

## 🚀 Features

### Core Features
- **Complete User Management**: 
  - Secure login system
  - Change username and password
  - Update personal information
  - Admin panel for user administration
  - Add and delete users (preserving their expenses)
- **Expense Management**: Add, view, update, and delete expenses
- **Interactive Dashboard**: Rich visualizations with Plotly charts
- **Partner Dashboard**: Combined expense view for couples/partners
- **Advanced Analytics**: Detailed spending analysis and trends
- **AI Financial Assistant**: Powered by CrewAI agents for personalized insights
- **Comprehensive Logging**: Production-ready logging system for monitoring and debugging

### AI Capabilities
- **Spending Pattern Analysis**: AI agents analyze your spending behavior
- **Budget Planning Advice**: Personalized budget recommendations
- **Savings Opportunities**: Identify areas to reduce expenses
- **Trend Analysis**: Understand your financial patterns over time

## 📋 Prerequisites

- Python 3.8+
- OpenAI API Key (for AI assistant features)

## 🛠️ Installation

1. **Clone the repository**

2. **Install required packages**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (Optional - for AI features)
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   SQL_URL=./data/expenses.db
   APP_ENV=development  # Change to 'production' for production environment
   ```

4. **Run the application in development mode**
   ```powershell
   streamlit run app.py
   ```

5. **For production deployment, refer to DEPLOYMENT_GUIDE.md**

## 🏃‍♂️ Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

### Default Login Credentials
- **Admin Users**: `admin` or `sana` with password `admin123`
- **Regular Users**: `user1` with password `user123`

These are for testing purposes only. You can add more users through the User Management interface.



## 📊 Application Structure

```
expense_tracker/
├── app.py              # Main Streamlit application
├── auth.py             # Authentication logic
├── database.py         # Database operations (SQLite)
├── dashboard.py        # Dashboard components and visualizations
├── manage_expenses.py  # Update and delete expenses functionality
├── user_management.py  # User management functionality
├── crew_agents.py      # CrewAI agents for financial insights
├── utils.py            # Utility functions and constants
├── logger.py           # Logging configuration and utilities
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── README.md           # This file
```

## 📝 Key Components

### Logging System
- **Separate Loggers**: Different components (database, auth, app) have dedicated loggers
- **Log Rotation**: Automatically rotates logs to prevent excessive file sizes
- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR, and CRITICAL levels for detailed troubleshooting
- **Context Managers**: Track execution time and catch exceptions

### User Management System
- **User Administration**: Admin-only interface for managing all users
- **Profile Management**: Users can update their own information
- **Password Security**: Strong password requirements with validation
- **Data Preservation**: User expenses are preserved even when accounts are deleted

## 🏷️ Expense Categories

The application includes predefined categories covering common expense types like Food & Dining, Transportation, Housing & Utilities, Healthcare, Entertainment, and more. Categories can be customized to meet specific needs.

## 📈 Dashboard Features

### Key Visualizations
- **Spending Overview**: Total spent, daily average, top category
- **Visual Analytics**: Pie charts, line charts, bar charts for spending trends
- **Category Breakdown**: Detailed spending by category
- **Recent Transactions**: Latest expense entries

### Analysis Options
- **Personal Dashboard**: Individual user expense tracking and visualization
- **Partner Dashboard**: Combined expense view for household management
- **Advanced Analysis**: Trends, patterns, and comparative spending analysis

## 🤖 AI Assistant Features

The AI assistant uses specialized CrewAI agents to provide intelligent financial insights:

- **Spending Pattern Analysis**: Identifies patterns and provides actionable recommendations
- **Budget Planning**: Offers optimization suggestions and warns about potential overruns
- **Savings Opportunities**: Identifies high-spending categories and suggests cost-cutting strategies

## 💾 Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `password_hash`: Hashed password
- `full_name`: User's full name
- `created_at`: Account creation timestamp

### Expenses Table
- `id`: Primary key
- `user_id`: Foreign key to users table
- `amount`: Expense amount
- `purpose`: Description of expense
- `category`: Expense category
- `date`: Date of expense
- `created_at`: Record creation timestamp

## 🔒 Security Features

- Password hashing using SHA-256
- Session-based authentication
- Strong password validation requirements
- Username format validation
- Input validation and sanitization
- SQL injection prevention through parameterized queries
- Role-based access control for admin features

## 📱 Usage Guide

### Managing Your User Profile
1. Navigate to "👤 User Management" (available to all users)
2. Go to the "✏️ My Profile" tab
3. Update your username, password, or personal information

### Adding Expenses
1. Navigate to "➕ Add Expense"
2. Enter amount, purpose, category, and date
3. Click "💾 Add Expense" to save

### Managing Expenses
1. Navigate to "✏️ Manage Expenses"
2. Select the expense to modify
3. Update expense details or delete as needed

### User Administration (Admin Only)
1. Navigate to "👤 User Management"
2. Use the "👥 All Users" tab to manage existing users
3. Use the "➕ Add User" tab to create new users
4. Perform actions like changing usernames, resetting passwords, or deleting accounts

### Viewing Dashboard
1. Go to "📊 Dashboard"
2. Use date filters to customize the view
3. Explore different charts and metrics

### Using AI Assistant
1. Navigate to "🤖 AI Assistant"
2. Choose analysis type:
   - Spending Pattern Analysis
   - Budget Planning Advice
   - Savings Opportunities
3. Click the respective button to get AI insights

### Exporting Data
1. Go to "📋 View Expenses"
2. Apply filters as needed
3. Click "📥 Export to CSV" to download data

## 🚨 Troubleshooting

### Common Issues

1. **Database not found**: The database is created automatically. Ensure the `data/` directory exists.

2. **AI features not working**: Check that your OpenAI API key is correctly set in the `.env` file.

3. **Login issues**: Use the default credentials provided above.

4. **Charts not displaying**: Ensure all dependencies are installed correctly.

5. **Password requirements**: Passwords must have at least 8 characters with uppercase, lowercase, digit, and special character.

6. **Username requirements**: Usernames must be 3-20 characters long and contain only letters, numbers, and underscores.

7. **Cannot delete your own account**: Admins cannot delete their own accounts while logged in.

### Error Messages

- **"No expenses found"**: Add some expenses first or adjust date filters
- **"Analysis unavailable"**: Check your OpenAI API key configuration
- **"Invalid username or password"**: Use the default credentials
- **"Username already exists"**: Choose a different username
- **"Current password is incorrect"**: Verify your current password when changing it
- **"Username is invalid"**: Follow the username format requirements

## 🔧 Customization

### Adding New Categories
Edit the `EXPENSE_CATEGORIES` list in `utils.py`:
```python
EXPENSE_CATEGORIES = [
    "🍔 Food & Dining",
    "🚗 Transportation",
    # Add your custom categories here
    "🎯 Your Custom Category"
]
```

## 📊 Performance Considerations

- The application uses SQLite for simplicity but can be upgraded to PostgreSQL for production
- Log rotation prevents excessive log file sizes
- Large datasets have filtering options for better performance

## 🔄 Future Enhancements

- [x] User management system
- [x] Expense update and deletion
- [x] Production-ready logging
- [ ] Budget setting and tracking
- [ ] Receipt image upload and OCR
- [ ] Bank account integration
- [ ] Mobile app version
- [ ] Multi-currency support
- [ ] Advanced reporting and analytics

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## 📞 Support

For support or questions, please create an issue in the project repository or contact the development team.