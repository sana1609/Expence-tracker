# Personal Expense Tracker with AI Assistant

A comprehensive expense tracking application built with Streamlit, featuring user authentication, interactive dashboards, and AI-powered financial insights using CrewAI agents.

## 🚀 Features

### Core Features
- **User Authentication**: Secure login system with 3 predefined users
- **Expense Management**: Add, view, and categorize expenses
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

1. **Clone or download the project files**
   ```bash
   mkdir expense_tracker
   cd expense_tracker
   ```

2. **Install required packages**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (Optional - for AI features)
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   SQL_URL=./data/expenses.db
   APP_ENV=development  # Change to 'production' for production environment
   ```

4. **Create the data directory**
   ```bash
   mkdir data
   ```

## 🏃‍♂️ Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## 🚀 Production Deployment

For production deployment, run:

```bash
python setup_production.py
```

This will:
- Create necessary directories
- Set up configuration files
- Configure logging
- Back up any existing data

See `DEPLOYMENT_GUIDE.md` for detailed deployment instructions.

## 👥 Default User Credentials

The application comes with 3 predefined users:

| Username | Password | Full Name |
|----------|----------|-----------|
| sana | admin@123$ | Sudhakar |
| harsi | admin@123$ | Harshitha |
| pandu | admin@123$ | swetha |

## 📊 Application Structure

```
expense_tracker/
├── app.py              # Main Streamlit application
├── auth.py             # Authentication logic
├── database.py         # Database operations (SQLite)
├── dashboard.py        # Dashboard components and visualizations
├── crew_agents.py      # CrewAI agents for financial insights
├── utils.py            # Utility functions and constants
├── logger.py           # Logging configuration and utilities
├── config.py           # Application configuration and settings
├── setup_production.py # Production setup script
├── requirements.txt    # Python dependencies
├── DEPLOYMENT_GUIDE.md # Deployment instructions
├── README.md           # This file
├── .env                # Environment variables (create this)
├── logs/               # Application logs directory
└── data/
    └── expenses.db     # SQLite database (auto-created)
```

## 📝 Logging System

The application includes a comprehensive logging system with:

- **Separate Loggers**: Different components (database, auth, app) have dedicated loggers
- **Log Rotation**: Automatically rotates logs to prevent excessive file sizes
- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR, and CRITICAL levels for detailed troubleshooting
- **Context Managers**: Track execution time and catch exceptions
- **Production Configuration**: Automatically adjusts log levels based on environment

## 🏷️ Expense Categories

The application includes 15 predefined categories:
- 🍔 Food & Dining
- 🚗 Transportation
- 🏠 Housing & Utilities
- 🛒 Groceries
- 💊 Healthcare
- 🎬 Entertainment
- 👕 Clothing
- 📚 Education
- 🎁 Gifts
- 💰 Savings & Investment
- 🔧 Maintenance
- ☎️ Communication
- ✈️ Travel
- 🏋️ Fitness
- 📱 Technology

## 📈 Dashboard Features

### Personal Dashboard
- **Spending Overview**: Total spent, daily average, top category
- **Visual Analytics**: 
  - Pie chart for category distribution
  - Line chart for daily spending trends
  - Bar chart for monthly comparisons
- **Category Breakdown**: Detailed spending by category
- **Recent Transactions**: Latest expense entries

### Partner Dashboard
- **Combined View**: See expenses from both partners
- **User Comparison**: Compare individual spending
- **Shared Analytics**: Combined category and trend analysis
- **Detailed Breakdown**: Sunburst chart showing user and category hierarchy

### Advanced Analysis
- **Personal Analysis**: Weekly patterns, average transaction sizes
- **Comparative Analysis**: Compare spending with other users
- **Trend Analysis**: Monthly trends with percentage changes

## 🤖 AI Assistant Features

The AI assistant uses CrewAI agents to provide intelligent financial insights:

### Financial Analyst Agent
- Analyzes spending patterns over the last 30 days
- Identifies concerning spending behaviors
- Provides actionable recommendations

### Budget Advisor Agent
- Compares current spending against budget
- Provides optimization suggestions
- Warns about potential budget overruns

### Savings Expert Agent
- Identifies categories with high spending
- Suggests cost-cutting strategies
- Recommends long-term savings approaches

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
- Input validation and sanitization
- SQL injection prevention through parameterized queries

## 📱 Usage Guide

### Adding Expenses
1. Navigate to "➕ Add Expense"
2. Enter amount, purpose, category, and date
3. Click "💾 Add Expense" to save

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

3. **Login issues**: Use the exact credentials provided in the table above.

4. **Charts not displaying**: Ensure all dependencies are installed correctly.

### Error Messages

- **"No expenses found"**: Add some expenses first or adjust date filters
- **"Analysis unavailable"**: Check your OpenAI API key configuration
- **"Invalid username or password"**: Use the predefined credentials

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

### Adding New Users
Modify the `create_default_users` function in `database.py`:
```python
default_users = [
    ("user1", "User One", "password123"),
    ("user2", "User Two", "password123"),
    ("partner", "Partner", "password123"),
    # Add new users here
    ("newuser", "New User", "newpassword")
]
```

### Customizing AI Agents
Modify the agent configurations in `crew_agents.py` to change their behavior, add new tools, or create additional agents.

## 📊 Performance Considerations

- The application uses SQLite for simplicity but can be upgraded to PostgreSQL for production
- AI features require OpenAI API calls which may have latency
- Large datasets may require pagination for better performance

## 🔄 Future Enhancements

- [ ] Budget setting and tracking
- [ ] Expense categories management
- [ ] Receipt image upload and OCR
- [ ] Bank account integration
- [ ] Mobile app version
- [ ] Multi-currency support
- [ ] Advanced reporting and analytics
- [ ] Expense approval workflows
- [ ] Integration with financial institutions

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## 📞 Support

For support or questions, please create an issue in the project repository or contact the development team.