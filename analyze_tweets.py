import re
from datetime import datetime
from collections import Counter
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup

# Read the HTML file
with open('outerhtml.txt', 'r', encoding='utf-8') as f:
    html_content = f.read()

# Parse HTML
soup = BeautifulSoup(html_content, 'html.parser')

# Find all time elements with datetime attributes
time_elements = soup.find_all('time', attrs={'datetime': True})

print(f"Found {len(time_elements)} total time elements")

# Extract timestamps and filter out retweets
tweet_times = []
for time_elem in time_elements:
    datetime_str = time_elem.get('datetime')

    # Check if this is part of a retweet by looking at parent elements
    # Retweets typically have "retweeted" text or specific data attributes
    parent_text = time_elem.parent.get_text() if time_elem.parent else ""

    # Look for retweet indicators in the surrounding context
    is_retweet = False
    current = time_elem
    for _ in range(5):  # Check up to 5 parent levels
        if current.parent:
            current = current.parent
            parent_str = str(current)
            # Check for retweet indicators
            if 'retweeted' in parent_str.lower() or 'data-testid="socialContext"' in parent_str:
                is_retweet = True
                break
        else:
            break

    if not is_retweet:
        try:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            tweet_times.append(dt)
        except:
            pass

print(f"Found {len(tweet_times)} tweet times (excluding retweets)")

# Extract hour of day
hours = [dt.hour for dt in tweet_times]

# Count tweets by hour
hour_counts = Counter(hours)

# Create histogram
plt.figure(figsize=(14, 6))
hours_range = range(24)
counts = [hour_counts.get(h, 0) for h in hours_range]

plt.bar(hours_range, counts, color='#1DA1F2', alpha=0.7, edgecolor='black')
plt.xlabel('Hour of Day (UTC)', fontsize=12)
plt.ylabel('Number of Tweets', fontsize=12)
plt.title('Tweet Distribution by Hour of Day (Excluding Retweets)', fontsize=14, fontweight='bold')
plt.xticks(hours_range)
plt.grid(axis='y', alpha=0.3)

# Add value labels on bars
for i, count in enumerate(counts):
    if count > 0:
        plt.text(i, count, str(count), ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig('tweet_histogram.png', dpi=300, bbox_inches='tight')
print("\nHistogram saved as 'tweet_histogram.png'")

# Print statistics
print("\n=== Tweet Time Statistics ===")
print(f"Total tweets analyzed: {len(tweet_times)}")
print(f"\nMost active hours (UTC):")
for hour, count in sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"  {hour:02d}:00 - {count} tweets")

plt.show()
