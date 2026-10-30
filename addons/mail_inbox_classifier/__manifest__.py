{
    "name": "Mail Inbox Classifier",
    "version": "18.0.1.0.0",
    "category": "Discuss",
    "summary": "Auto-categorize incoming emails (customer support, order history, query, other) by keyword matching",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/mail_inbox_message_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
