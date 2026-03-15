# GapSense Teacher Demo Web UI

## 🎯 Overview

A beautiful, WhatsApp-like web interface that simulates the complete teacher flow for demos and testing. Perfect for showcasing GapSense functionality without needing WhatsApp API approval.

**Demo URL:** `http://your-domain.com/demo`

## ✨ Features

- **WhatsApp-Style UI** - Modern chat interface with smooth animations
- **Complete Teacher Flow** - Full onboarding, student management, and gap analysis
- **Exercise Book Upload** - Image upload with student selection
- **Real-Time Commands** - `/STATUS`, `/GAPS`, `/STUDENT` commands work exactly like WhatsApp
- **Mobile-First Design** - Responsive and touch-friendly
- **Live Backend** - Uses the same services as production WhatsApp flow

## 🚀 Quick Start

### Local Development

1. **Start the server:**
   ```bash
   docker compose up -d db web
   ```

2. **Access the demo:**
   ```
   http://localhost:8000/demo
   ```

3. **Start interacting:**
   - Type "START" to begin onboarding
   - Upload exercise book photos
   - Use commands: /STATUS, /GAPS, /STUDENT

### Production Deployment

The demo UI is automatically included when you deploy GapSense. No additional configuration needed!

```bash
# Deploy as usual
docker compose up -d

# Demo will be available at:
# https://your-domain.com/demo
```

## 📱 Using the Demo

### Teacher Onboarding Flow

1. **Start Onboarding**
   - Click "🚀 Start" or type "START"
   - System asks for school name

2. **Provide School Name**
   - Type your school name (e.g., "St. Mary's JHS, Accra")
   - System asks for class name

3. **Provide Class Name**
   - Type class name (e.g., "Grade 7A" or "JHS 1")
   - System asks for student count

4. **Provide Student Count**
   - Type number (e.g., "25")
   - System asks for student names

5. **Provide Student List**
   - Enter names (one per line or comma-separated):
     ```
     Kwame Mensah
     Ama Asante
     Kofi Boateng
     ```
   - System creates student profiles
   - Onboarding complete! ✅

### Exercise Book Scanning

1. **Upload Photo**
   - Click 📎 button
   - Select exercise book photo from device
   - System shows student selection

2. **Select Student**
   - Type student number (e.g., "1" for first student)
   - System confirms: "Analyzing [Student]'s exercise book..."

3. **View Results**
   - Wait ~30 seconds (simulated)
   - System displays gaps identified
   - Use `/STUDENT <name>` for full report

### Teacher Commands

**Class Overview:**
```
/STATUS
```
Shows:
- Students scanned count
- Last scan date
- Top 3 common gaps
- Week-over-week improvement %

**Gap Breakdown:**
```
/GAPS
```
Shows:
- All gaps sorted by frequency
- Number of students affected
- Severity ratings

**Individual Student Report:**
```
/STUDENT Kwame
```
Shows:
- Last scan date
- All gaps identified
- Primary gap (root cause)
- Recommended actions
- Estimated intervention time

## 🎨 UI/UX Features

### Design Elements

- **Gradient Background** - Purple gradient for modern look
- **WhatsApp-Like Bubbles** - Familiar chat interface
- **Smooth Animations** - Slide-in messages, typing indicators
- **Quick Action Buttons** - One-tap access to common commands
- **Responsive Layout** - Works on desktop, tablet, and mobile
- **Touch-Friendly** - Large tap targets, swipe-friendly

### User Experience

- **Typing Indicators** - Shows "..." when system is processing
- **Message Timestamps** - All messages timestamped
- **Auto-Scroll** - Automatically scrolls to latest message
- **Status Badge** - Shows onboarding status in header
- **Error Handling** - Clear error messages with emoji
- **Help Modal** - Built-in command reference

## 🛠️ Technical Details

### Architecture

```
User Browser
    ↓
FastAPI Demo Routes (/demo/api/*)
    ↓
Mock WhatsApp Client (captures messages)
    ↓
TeacherFlowExecutor (same as WhatsApp flow)
    ↓
ClassGapAnalyzer, ExerciseBookScanner, etc.
    ↓
Database (PostgreSQL)
```

### Key Files

- `src/gapsense/web/demo.py` - Demo API routes
- `src/gapsense/web/templates/demo.html` - UI template
- `src/gapsense/web/mock_whatsapp.py` - Mock WhatsApp client
- `src/gapsense/engagement/teacher_flows.py` - Teacher flow logic (shared with WhatsApp)

### Data Persistence

- Each demo session creates a real teacher in the database
- Demo phone: `+233501234567` (configurable)
- Students, gap profiles, and reports are real database records
- Multiple demos can run simultaneously with different phone numbers

## 📊 Demo Scenarios

### Scenario 1: Quick Class Overview

```
1. Type: START
2. School: Demo School
3. Class: Grade 7A
4. Students: 3
5. Names: Alice, Bob, Charlie
6. Type: /STATUS
   → Shows class status
```

### Scenario 2: Exercise Book Analysis

```
1. Complete onboarding (as above)
2. Click 📎 → Upload exercise book photo
3. Select student: 1
4. Wait for analysis
5. Type: /STUDENT Alice
   → Shows detailed gap report
```

### Scenario 3: Gap Analysis Workflow

```
1. Complete onboarding
2. Upload 3 different exercise books
3. Type: /STATUS
   → Shows common gaps across class
4. Type: /GAPS
   → Shows detailed gap breakdown
5. Type: /STUDENT <name>
   → Individual reports for each student
```

## 🎭 Demo Tips for Presentations

### Before Your Demo

1. **Reset Database** (optional, for clean demo):
   ```bash
   docker compose exec db psql -U gapsense -c "TRUNCATE teachers CASCADE;"
   ```

2. **Prepare Sample Images**
   - Have 2-3 exercise book photos ready
   - Use clear, well-lit photos
   - Different students, different topics

3. **Test Flow Once**
   - Run through complete onboarding
   - Upload one image to verify
   - Test all commands

### During Your Demo

1. **Start Fresh**
   - Show welcome screen
   - Highlight WhatsApp-like UI
   - Point out quick action buttons

2. **Show Onboarding**
   - Walk through each step
   - Explain how teachers would use this
   - Show bulk student upload

3. **Demonstrate Image Upload**
   - Upload exercise book photo
   - Show student selection
   - Wait for analysis (or skip ahead)

4. **Show Reporting**
   - Run /STATUS command
   - Run /GAPS command
   - Run /STUDENT command
   - Highlight actionable insights

5. **Explain Value**
   - "This is exactly how it works on WhatsApp"
   - "Teachers already know how to use chat"
   - "No app download needed"
   - "Works on any phone"

## 🔧 Customization

### Change Demo Phone Number

Edit `src/gapsense/web/templates/demo.html`:

```javascript
const TEACHER_PHONE = '+233501234567'; // Change this
```

### Add Custom Branding

Edit the header in `demo.html`:

```html
<div class="header-title">🎓 Your School Name</div>
<div class="header-subtitle">AI Teaching Assistant</div>
```

### Modify Colors

Edit CSS in `demo.html`:

```css
/* Primary color (buttons, header) */
background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);

/* Message bubbles */
background: #dcf8c6; /* Sent messages */
background: white;   /* Received messages */
```

## 🐛 Troubleshooting

### Demo not loading

**Check server status:**
```bash
docker compose logs web --tail=50
```

**Verify route registration:**
```bash
curl http://localhost:8000/demo
```

### Messages not appearing

**Check browser console for JavaScript errors:**
- Open DevTools (F12)
- Check Console tab
- Look for red error messages

**Check API responses:**
```bash
curl -X POST http://localhost:8000/demo/api/message \
  -F "message=START" \
  -F "teacher_phone=+233501234567"
```

### Image upload failing

**Check file size:**
- Maximum upload size: 10MB (configurable)
- Supported formats: JPG, PNG, GIF

**Check API logs:**
```bash
docker compose logs web -f | grep upload
```

## 📈 Next Steps

Once Twilio WhatsApp API is approved (1-2 weeks):

1. The exact same backend flows will work on WhatsApp
2. Teachers will use WhatsApp instead of this web UI
3. This demo remains available for training and support
4. Consider adding authentication for demo access in production

## 🎓 Training Materials

Use this demo to train:
- **Teachers** - Show them what the WhatsApp experience will be like
- **School Admins** - Demonstrate gap analysis capabilities
- **Partners/Funders** - Showcase the complete solution
- **Technical Team** - Test flows before WhatsApp approval

## 🚀 AWS Deployment

The demo UI will deploy automatically with your GapSense instance:

```bash
# No additional steps needed!
# Follow DEPLOYMENT_CHECKLIST.md as usual
# Demo will be available at: https://your-domain.com/demo
```

## 💡 Pro Tips

- **Use it for user testing** - Get feedback before WhatsApp launch
- **Create demo videos** - Record screen while using demo UI
- **Generate sample data** - Create realistic student/gap data for demos
- **Share the link** - Send demo URL to stakeholders for async review
- **Mobile first** - Always test on actual mobile devices

---

**Ready to demo?** Just open `http://localhost:8000/demo` and type **START**! 🚀
