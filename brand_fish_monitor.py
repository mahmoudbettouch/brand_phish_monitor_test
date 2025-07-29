#!/usr/bin/env python
# Copyright (c) 2017 @x0rz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import re
import math
import certstream
import tqdm
import yaml
import time
import os
import json
from datetime import datetime, timedelta, timezone
from Levenshtein import distance
from termcolor import colored
from tld import get_tld
import smtplib
from email.mime.text import MIMEText
from Levenshtein import ratio 
from fuzzywuzzy import fuzz
from confusables import unconfuse

# Global variables to be set from config
config = None
brands = None
whitelist = None
pbar = None
log_file = None
alert_history = {}
stats_file = None

def load_config():
    global stats_file
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        with open(config['files']['brands_yaml'], 'r') as f:
            brands_data = yaml.safe_load(f)
            brands = brands_data.get('brands', [])

        with open(config['files']['whitelist_yaml'], 'r') as f:
            whitelist_data = yaml.safe_load(f)
            whitelist = set(whitelist_data.get('whitelist', []))

        log_file = config['files']['log_file'].replace("{date}", time.strftime("%Y-%m-%d"))
        stats_file = config['files']['stats_file']

        # Load alert history for cooldown
        if os.path.exists(stats_file):
            with open(stats_file, 'r') as f:
                try:
                    alert_history.update(json.load(f))
                except Exception:
                    pass  # If file is corrupted or empty, skip it

        return config, brands, whitelist, log_file, stats_file

    except Exception as e:
        print(f"Error loading configuration: {e}")
        exit(1)

def save_alert_history(stats_file):
    with open(stats_file, 'w') as f:
        json.dump(alert_history, f)

def is_whitelisted(domain, whitelist):
    for whitelisted_domain in whitelist:
        if domain.endswith(f"{whitelisted_domain}") or domain == whitelisted_domain:
            return True
    return False 

def entropy(string):
    """Calculates the Shannon entropy of a string"""
    prob = [ float(string.count(c)) / len(string) for c in dict.fromkeys(list(string)) ]
    entropy = - sum([ p * math.log(p) / math.log(2.0) for p in prob ])
    return entropy

def send_email(subject, body, smtp_config):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_config['sender']
    msg['To'] = ', '.join(smtp_config['recipients'])

    with smtplib.SMTP_SSL(smtp_config['server'], smtp_config['port']) as server:
        if smtp_config['use_auth']:
            server.login(smtp_config['username'], smtp_config['password'])
        server.sendmail(smtp_config['sender'], smtp_config['recipients'], msg.as_string())

    print("Email sent.")

def score_domain(domain, brands, config):
    """Score domain for phishing likelihood based on brand similarity and domain structure."""
    score = 0

    suspicious_tlds = ['.tk', '.top', '.gq', '.ml', '.cf', '.xyz', '.cfd', '.online']
    for tld in suspicious_tlds:
        if domain.endswith(tld):
            score += 10
            break

    if domain.startswith('*.'):
        domain = domain[2:]

    try:
        res = get_tld(domain, as_object=True, fail_silently=True, fix_protocol=True)
        domain_body = '.'.join([res.subdomain, res.domain])
    except Exception:
        domain_body = domain

    score += int(round(entropy(domain_body) * 10))

    domain_body = unconfuse(domain_body)
    words_in_domain = re.split(r"\W+", domain_body)

    if words_in_domain[0] in ['com', 'net', 'org']:
        score += 10

    for brand in brands:
        if brand in domain_body:
            score += 90

        for word in [w for w in words_in_domain if w not in ['email', 'mail', 'cloud']]:
            if distance(word, brand) == 1:
                score += 70
            elif distance(word, brand) == 2:
                score += 40

    if 'xn--' not in domain and domain.count('-') >= 4:
        score += domain.count('-')

    if domain.count('.') >= 3:
        score += domain.count('.')

    best_similarity = 0
    best_brand = None
    for brand in brands:
        for word in words_in_domain:
            sim = fuzz.ratio(brand, word) / 100.0
            if sim > best_similarity:
                best_similarity = sim
                best_brand = brand
    similarity_percentage = int(best_similarity * 100)

    return score, best_brand

def callback(message, context):
    if message['message_type'] != "certificate_update":
        return

    domains = message['data']['leaf_cert']['all_domains']
    cooldown_days = config['cooldown'].get('domain_cooldown', 0)
    now = datetime.now(timezone.utc)

    for domain in domains:
        raw_domain = domain.lower()

        domain = raw_domain[2:] if domain.startswith('*.') else raw_domain

        if domain in whitelist or any(domain.endswith(w) for w in whitelist):
            continue
        

        pbar.update(1)
        score, brand = score_domain(domain, brands, config)

        issuer = message['data']['leaf_cert']['issuer'].get('O', '')
        if issuer == "Let's Encrypt":
            score += 10

        if score >= config['detection']['min_score'] and brand:
            last_alert_time = alert_history.get(domain)
            if last_alert_time:
                last_time = datetime.fromisoformat(last_alert_time)
                if now - last_time < timedelta(days=cooldown_days):
                    continue  # Skip alerting due to cooldown

            alert = f"[!] Alert: {colored(domain, 'red')} (score={score}, brand={brand})"
            tqdm.tqdm.write(alert)

            body = f"Domain: {domain}\nTarget Brand: {brand}\nScore: {score}"
            subject = config['smtp']['subject_template'].format(domain=domain, brand=brand, score=score)

            if config['smtp']['enabled']:
                send_email(subject, body, config['smtp'])

            with open(log_file, 'a') as f:
                f.write(f"{domain}\n")

            alert_history[domain] = now.isoformat()
            save_alert_history(stats_file)

        elif score >= 72:
            alert = f"[!] Suspicious: {colored(domain, 'yellow')} (score={score}, brand={brand})"
            tqdm.tqdm.write(alert)

if __name__ == '__main__':
    config, brands, whitelist, log_file, stats_file = load_config()
    pbar = tqdm.tqdm(desc='certificate_update', unit='cert')
    certstream.listen_for_events(callback, url=config['certstream_url'])
