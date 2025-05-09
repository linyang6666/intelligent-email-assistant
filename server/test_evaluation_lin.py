#!/usr/bin/env python3

import time
import sys
from memory_profiler import memory_usage
from gmail_connector import GmailConnector
from email_classifier import EmailClassifier

def fetch_sample_emails(count=20):
    connector = GmailConnector()
    connector.authenticate()
    return connector.get_recent_emails(max_emails=count)

def evaluate_classification(emails, human_labels):
    classifier = EmailClassifier()
    processed = classifier.classify_emails(emails, max_emails=len(emails))
    preds = [e.get('tag', 'default') for e in processed]
    correct = sum(1 for p,h in zip(preds, human_labels) if p == h)
    accuracy = correct / len(emails) * 100
    return accuracy, preds, processed

def evaluate_spam(emails, human_spam_flags):
    classifier = EmailClassifier()
    flags = [classifier.is_spam(e) for e in emails]
    correct = sum(1 for f,h in zip(flags, human_spam_flags) if f == h)
    accuracy = correct / len(emails) * 100
    return accuracy, flags

def measure_performance(emails):
    classifier = EmailClassifier()
    # peak memory during classification
    mem_usage = memory_usage(
        (classifier.classify_emails, (emails, len(emails))),
        max_iterations=1
    )
    # wall‐clock time
    start = time.time()
    classifier.classify_emails(emails, max_emails=len(emails))
    resp_time = time.time() - start
    rate = len(emails) / resp_time * 60  # emails/min
    return resp_time, rate, max(mem_usage)

if __name__ == "__main__":
    SAMPLE_COUNT = 20
    print(f"\n1) Fetching {SAMPLE_COUNT} sample emails…\n")
    emails = fetch_sample_emails(SAMPLE_COUNT)

    print("2) Sample emails (index: Subject — From):")
    for i, e in enumerate(emails, 1):
        print(f"  {i:2d}. {e['subject']!r}  —  {e['sender']}")

    # MANUAL STEP: fill in these two lists with our ground truth
    human_labels = [
        'urgent',  # 1. Security alert
        'spam',    # 2. Lorde promo
        'urgent',  # 3. Security alert
        'urgent',  # 4. Security alert
        'spam',    # 5. Sony promo
        'business',# 6. Gemini tutorial
        'spam',    # 7. Music promo
        'spam',    # 8. Headphones promo
        'business',# 9. AI Studio tutorial
        'spam',    #10. OneKeyCash expiry (treat as spam)
        'spam',    #11. Ticket promo
        'business',#12. AI Studio onboarding
        'urgent',  #13. Security alert
        'spam',    #14. Spotify promo
        'spam',    #15. Loyalty changes promo
        'urgent',  #16. Security alert
        'urgent',  #17. Security alert
        'spam',    #18. Music fan event
        'spam',    #19. Music fan event
        'spam'     #20. Music fan event
    ]
    human_spam_flags = [
        False, True, False, False,
        True, False, True, True,
        False, True, True, False,
        False, True, True, False,
        False, True, True, True
    ]
    

    if len(human_labels) != SAMPLE_COUNT or len(human_spam_flags) != SAMPLE_COUNT:
        print(f"\n>> You must supply exactly {SAMPLE_COUNT} entries in each list. Exiting.")
        sys.exit(1)

    # 4) Evaluate
    class_acc, preds, processed = evaluate_classification(emails, human_labels)
    spam_acc, flags = evaluate_spam(emails, human_spam_flags)
    resp_time, proc_rate, mem_used = measure_performance(emails)

    # 5) Print summary
    print("\n=== Evaluation Results ===")
    print(f"• Classification Accuracy : {class_acc:5.2f}%")
    print(f"• Spam Detection Accuracy : {spam_acc:5.2f}%")
    print(f"• Response Time (batch)   : {resp_time:.2f} seconds")
    print(f"• Processing Rate         : {proc_rate:.1f} emails/minute")
    print(f"• Peak Memory Usage       : {mem_used:.1f} MiB")

    # 6) Show which emails were wrong
    print("\n=== Classification Errors ===")
    for i, (h, p) in enumerate(zip(human_labels, preds), start=1):
        if h != p:
            subj = emails[i-1]['subject']
            sndr = emails[i-1]['sender']
            print(f" {i:2d}. Predicted={p!r}, Actual={h!r} — \"{subj}\" from {sndr}")

    print("\n=== Spam Detection Errors ===")
    for i, (h, p) in enumerate(zip(human_spam_flags, flags), start=1):
        if h != p:
            subj = emails[i-1]['subject']
            sndr = emails[i-1]['sender']
            print(f" {i:2d}. Predicted={'spam' if p else 'not spam'}, "
                  f"Actual={'spam' if h else 'not spam'} — \"{subj}\" from {sndr}")
