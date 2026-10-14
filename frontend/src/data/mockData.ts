import type { MonitoredWebsite, ChangeRecord, DeadlineItem, NotificationItem, DashboardSummary } from '../types';

/**
 * DEMONSTRATION DATA
 * Used strictly for frontend visual prototyping and preview when the backend is offline.
 * Clearly separated from real API calls.
 */

export const MOCK_WEBSITES: MonitoredWebsite[] = [
  {
    id: 1,
    name: "GTU Examination Notices & Circulars",
    url: "https://www.gtu.ac.in/Circular.aspx",
    category: "University",
    selector: ".circular-list",
    check_interval_minutes: 30,
    status: "active",
    last_checked_at: "5 minutes ago",
    last_change_at: "Today, 19:40",
    change_count: 8,
    created_at: "2026-10-01"
  },
  {
    id: 2,
    name: "NPTEL Swayam Assignment Portal",
    url: "https://swayam.gov.in/nc_details/NPTEL",
    category: "Academics",
    selector: "#timeline-announcements",
    check_interval_minutes: 60,
    status: "active",
    last_checked_at: "18 minutes ago",
    last_change_at: "Yesterday, 16:20",
    change_count: 3,
    created_at: "2026-10-02"
  },
  {
    id: 3,
    name: "ACM Student Chapter Hackathon Hub",
    url: "https://studentevents.college.edu/hackathon",
    category: "Competitions",
    selector: ".announcement-card",
    check_interval_minutes: 120,
    status: "warning",
    last_checked_at: "45 minutes ago",
    last_change_at: "Oct 11, 14:10",
    change_count: 5,
    created_at: "2026-10-05"
  },
  {
    id: 4,
    name: "National Scholarship Scheme Portal",
    url: "https://scholarships.gov.in",
    category: "Financial Aid",
    selector: "#scholarship-deadlines",
    check_interval_minutes: 240,
    status: "active",
    last_checked_at: "1 hour ago",
    last_change_at: "Oct 10, 12:00",
    change_count: 2,
    created_at: "2026-10-06"
  },
  {
    id: 5,
    name: "Department Internship Bulletin Board",
    url: "https://placement.college.edu/internships",
    category: "Career",
    selector: ".feed-items",
    check_interval_minutes: 60,
    status: "active",
    last_checked_at: "12 minutes ago",
    last_change_at: "Oct 09, 11:15",
    change_count: 4,
    created_at: "2026-10-08"
  }
];

export const MOCK_CHANGES: ChangeRecord[] = [
  {
    id: 101,
    website_id: 1,
    website_name: "GTU Examination Notices & Circulars",
    detected_at: "Today at 19:40 IST",
    summary: "Updated Winter 2026 Practical Exam Time Table schedule",
    change_type: "modification",
    additions_count: 14,
    deletions_count: 6,
    old_content_snippet: 
`[Oct 08, 2026] Circular: BE Sem 5 Practical Examination schedule will be notified after Diwali vacation.
Colleges are requested to finalize internal marks submission by Oct 18, 2026.
External viva dates pending university ratification.`,
    new_content_snippet: 
`[Oct 13, 2026] URGENT CIRCULAR: Winter 2026 B.E. Sem 5 Practical Examination finalized.
Examination Window: Oct 28 to Nov 05, 2026 across all affiliated zonal centers.
Student hall tickets will be issued online starting Oct 22, 2026.
No extension requests will be entertained.`,
    is_read: false
  },
  {
    id: 102,
    website_id: 2,
    website_name: "NPTEL Swayam Assignment Portal",
    detected_at: "Yesterday at 16:20 IST",
    summary: "Assignment 8 Deadline extended by 4 days due to server downtime",
    change_type: "addition",
    additions_count: 8,
    deletions_count: 2,
    old_content_snippet:
`Course: Cloud Computing & Distributed Architecture
Week 8 Assignment Due: Oct 14, 2026 23:59 IST.
Assignments submitted after the deadline will receive a zero mark.`,
    new_content_snippet:
`Course: Cloud Computing & Distributed Architecture
Week 8 Assignment Due: Oct 18, 2026 23:59 IST (EXTENDED).
NOTE: Cloud server maintenance scheduled for Oct 14 has prompted a 4-day grace extension.
Week 9 materials remain on schedule.`,
    is_read: true
  },
  {
    id: 103,
    website_id: 3,
    website_name: "ACM Student Chapter Hackathon Hub",
    detected_at: "Oct 11 at 14:10 IST",
    summary: "Added problem statement tracks for AI/ML & Web3 with updated prize pool",
    change_type: "modification",
    additions_count: 22,
    deletions_count: 4,
    old_content_snippet:
`Annual 36-Hour Hackathon - Innovate2026
Tracks will be unlocked on Oct 15 during the opening keynote.
Registration closing date: Oct 16.`,
    new_content_snippet:
`Annual 36-Hour Hackathon - Innovate2026
PRIZE POOL EXPANDED: Total ₹50,000 cash prizes sponsored by tech partners!
Track 1: AI Agent Workflows & Student Productivity Tools
Track 2: Decentralized Verifiable Identity & Credentials
Track 3: Smart Campus Automation & Sustainability
Registration closes Oct 16 strictly at 18:00 IST.`,
    is_read: true
  },
  {
    id: 104,
    website_id: 5,
    website_name: "Department Internship Bulletin Board",
    detected_at: "Oct 09 at 11:15 IST",
    summary: "New Summer 2027 Research Internship opportunity at ISRO Space Applications Centre",
    change_type: "addition",
    additions_count: 12,
    deletions_count: 0,
    old_content_snippet: `No active openings listed for Semester 6 prerequisites.`,
    new_content_snippet: 
`[NEW OPENING] ISRO SAC Ahmedabad: Summer Undergraduate Internship in Satellite Image Processing.
Eligibility: 6th Sem B.E. Computer Engineering / IT with CPI > 7.5.
Last date to apply through college TPO: Oct 25, 2026.`,
    is_read: true
  }
];

export const MOCK_DEADLINES: DeadlineItem[] = [
  {
    id: 1,
    website_id: 3,
    title: "Hackathon Team Registration & Problem Selection",
    due_date: "Oct 16, 2026",
    days_left: 3,
    source_url: "https://studentevents.college.edu/hackathon",
    priority: "high",
    status: "critical",
    category: "Competitions",
    description: "Final cutoff to lock team member names (max 4 students) and reserve workstation desks."
  },
  {
    id: 2,
    website_id: 2,
    title: "NPTEL Week 8 Assignment Final Submission",
    due_date: "Oct 18, 2026",
    days_left: 5,
    source_url: "https://swayam.gov.in/nc_details/NPTEL",
    priority: "high",
    status: "upcoming",
    category: "Academics",
    description: "Extended deadline for 15 multiple choice and programming questions."
  },
  {
    id: 3,
    website_id: 1,
    title: "GTU Hall Ticket Verification & Download",
    due_date: "Oct 22, 2026",
    days_left: 9,
    source_url: "https://www.gtu.ac.in/Circular.aspx",
    priority: "high",
    status: "upcoming",
    category: "Exams",
    description: "Download student exam admit card and obtain principal seal from department admin."
  },
  {
    id: 4,
    website_id: 5,
    title: "ISRO SAC Internship Application via TPO",
    due_date: "Oct 25, 2026",
    days_left: 12,
    source_url: "https://placement.college.edu/internships",
    priority: "medium",
    status: "upcoming",
    category: "Internships",
    description: "Submit attested 4th & 5th sem marksheets, resume, and NOC recommendation."
  },
  {
    id: 5,
    website_id: 4,
    title: "National Scholarship Scheme (NSP) Portal Closes",
    due_date: "Oct 31, 2026",
    days_left: 18,
    source_url: "https://scholarships.gov.in",
    priority: "medium",
    status: "upcoming",
    category: "Scholarships",
    description: "Annual renewal deadline for central sector scholarship for college students."
  }
];

export const MOCK_NOTIFICATIONS: NotificationItem[] = [
  {
    id: 1,
    type: "change",
    title: "Exam Schedule Updated",
    message: "GTU Examination Notices updated the practical timetable for Winter 2026 semester 5.",
    created_at: "20 minutes ago",
    is_read: false,
    target_url: "https://www.gtu.ac.in/Circular.aspx"
  },
  {
    id: 2,
    type: "deadline",
    title: "Critical Deadline Approaching",
    message: "ACM Student Chapter Hackathon team registration closes in 3 days (Oct 16).",
    created_at: "2 hours ago",
    is_read: false,
    target_url: "https://studentevents.college.edu/hackathon"
  },
  {
    id: 3,
    type: "change",
    title: "Assignment Due Date Extended",
    message: "NPTEL Swayam Week 8 deadline has been pushed forward to Oct 18, 2026.",
    created_at: "Yesterday, 16:20",
    is_read: true,
    target_url: "https://swayam.gov.in/nc_details/NPTEL"
  },
  {
    id: 4,
    type: "system",
    title: "Automated Webpage Health Check",
    message: "All 5 active monitors polled successfully. No HTTP 404 or connection failures.",
    created_at: "Yesterday, 12:00",
    is_read: true
  }
];

export const MOCK_SUMMARY: DashboardSummary = {
  active_monitors_count: 5,
  total_changes_detected: 22,
  upcoming_deadlines_count: 5,
  unread_notifications_count: 2,
  health_status: "Healthy"
};
