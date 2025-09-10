import pandas as pd
import requests
import time
import os
import re
import json
from difflib import SequenceMatcher

def is_valid_disease_name(disease_name):
    """
    Check if the disease name is likely a real disease (not a category/module)
    """
    if pd.isna(disease_name) or disease_name.strip() == "":
        return False
    
    disease_name = disease_name.strip()
    
    # Skip if it's just dashes or module names
    if re.match(r'^-+\s*(Module|Traditional medicine)', disease_name, re.IGNORECASE):
        return False
    
    # Skip if it's just category headers (broad categories) - but be less restrictive
    broad_categories = [
        'Traditional medicine disorders',
        'Module'
    ]
    
    clean_name = re.sub(r'^[-\s]*', '', disease_name).strip()
    clean_name = re.sub(r'\s*\([^)]*\)$', '', clean_name)
    
    for category in broad_categories:
        if clean_name.lower() == category.lower():
            return False
    
    # Be less restrictive - allow shorter names and broader categories
    if len(clean_name) < 5:  # Very short names are usually categories
        return False
    
    # Allow broader categories that might contain specific diseases
    return True

def clean_disease_name(disease_name):
    """
    Clean the disease name by removing leading dashes and extra spaces
    """
    if pd.isna(disease_name):
        return disease_name
    
    # Remove all leading dashes and spaces
    cleaned = re.sub(r'^[-\s]*', '', disease_name.strip())
    # Remove content in parentheses like (TM2) if it's at the end
    cleaned = re.sub(r'\s*\([^)]*\)$', '', cleaned)
    # Remove leading qualifiers like "Other specified" / "Unspecified" / "Other"
    cleaned = re.sub(r'^\s*(other\s+specified|unspecified|other)\b[:\-\s]*', '', cleaned, flags=re.IGNORECASE)
    # Remove inline qualifiers that are not symptoms
    qualifiers_patterns = [
        r'\bother specified\b', r'\bunspecified\b', r'\bnot elsewhere classified\b', r'\bnec\b', r'\bnos\b'
    ]
    for qp in qualifiers_patterns:
        cleaned = re.sub(qp, '', cleaned, flags=re.IGNORECASE)
    # Compact whitespace
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    return cleaned.strip()

def extract_key_medical_terms(disease_name):
    """
    Extract the most important medical terms from a disease name
    """
    # Common medical suffixes that can be optional
    optional_suffixes = ['disease', 'disorder', 'disorders', 'syndrome', 'condition', 'illness', 'attack', 'episode']

    # Qualifier tokens to exclude from core terms
    non_symptom_terms = set([
        'other', 'specified', 'unspecified', 'general', 'nec', 'nos', 'tm2', 'tm', 'module', 'chapter',
        'traditional', 'medicine', 'due', 'resulting', 'related', 'type', 'level'
    ])

    # Recognize important multi-word medical phrases so we don't reduce them to a generic last word
    multiword_phrases = [
        'central nervous system', 'nervous system', 'immune system', 'respiratory system', 'digestive system',
        'cardiovascular system', 'circulatory system', 'musculoskeletal system', 'endocrine system',
        'urinary system', 'reproductive system', 'integumentary system', 'lymphatic system', 'auditory system',
        'visual system'
    ]

    found_phrases = []
    # Ensure cleaned, lowercased text is available for phrase detection
    name_l = clean_disease_name(disease_name).lower().strip()
    remaining = name_l
    for phrase in multiword_phrases:
        if phrase in remaining:
            found_phrases.append(phrase)
            # remove phrase tokens from remaining consideration (basic removal)
            remaining = remaining.replace(phrase, ' ')

    # Split the remaining into words
    words = remaining.split()

    # Remove very common connecting words
    stop_words = ['and', 'or', 'of', 'the', 'with', 'in', 'to', 'for', 'by']
    meaningful_words = [w for w in words if w not in stop_words]

    # Identify core single-word terms (avoid adding generic 'system' when a phrase exists)
    core_terms_words = []
    for word in meaningful_words:
        if word in optional_suffixes:
            continue
        if word == 'system' and found_phrases:
            # skip generic 'system' if a specific system phrase was found
            continue
        if word in non_symptom_terms:
            continue
        core_terms_words.append(word)
        if len(core_terms_words) >= 2:
            break

    # Prioritize phrases; then add individual core words
    core_terms: list[str] = []
    core_terms.extend(found_phrases[:2])
    for w in core_terms_words:
        if w not in core_terms and w not in non_symptom_terms:
            core_terms.append(w)
        if len(core_terms) >= 3:  # keep it compact
            break

    return core_terms

def calculate_similarity(s1, s2):
    """
    Calculate similarity between two strings using SequenceMatcher
    """
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

def find_best_wikipedia_match(disease_query, search_results):
    """
    Improved Wikipedia matching with better medical term recognition
    """
    if not search_results or 'pages' not in search_results:
        return None
    
    pages = search_results['pages']
    if not pages:
        return None
    
    best_match = None
    best_score = 0
    
    disease_lower = disease_query.lower()
    disease_words = set(disease_lower.split())
    
    # Extract core medical terms for better matching
    core_terms = extract_key_medical_terms(disease_query)
    core_words = set(core_terms)
    
    print(f"    Core medical terms extracted: {core_terms}")
    
    for page in pages[:20]:  # Check more results
        title = page.get('title', '').lower()
        description = page.get('description', '').lower()
        
        # Calculate different similarity scores
        title_similarity = calculate_similarity(disease_lower, title)
        
        # Check for exact word matches with original query
        title_words = set(title.split())
        word_overlap = len(disease_words.intersection(title_words)) / len(disease_words) if disease_words else 0
        
        # Check for core medical term matches (MUCH higher weight)
        core_overlap = len(core_words.intersection(title_words)) / len(core_words) if core_words else 0
        
        # Special boost for exact core term matches
        exact_core_match = any(core_term in title for core_term in core_terms)
        core_boost = 0.4 if exact_core_match else 0
        
        # Check if it's a medical/disease-related page
        medical_keywords = ['disease', 'syndrome', 'disorder', 'condition', 'illness', 'infection', 'attack', 'episode']
        is_medical = any(keyword in title or keyword in description for keyword in medical_keywords)
        
        # Medical relevance boost
        medical_boost = 0.2 if is_medical else 0
        
        # Avoid disambiguation pages (strong penalty)
        is_disambiguation = 'disambiguation' in title or 'may refer to' in description
        disambiguation_penalty = 0.5 if is_disambiguation else 0
        
        # Penalize generic/category-like pages
        generic_terms = [
            'category:', 'list of', 'module', 'traditional medicine', 'unspecified', 'other specified',
            'classification', 'terminology', 'outline of', 'index of', 'tm2'
        ]
        looks_generic = any(g in title for g in generic_terms) or any(g in description for g in generic_terms)

        # Calculate composite score with enhanced core term weighting
        composite_score = (
            title_similarity * 0.3 +          # Title similarity
            word_overlap * 0.2 +              # Word overlap from full query
            core_overlap * 0.3 +              # Core medical term overlap
            core_boost +                      # Exact core term match boost
            medical_boost -                   # Medical relevance boost
            disambiguation_penalty -          # Strong penalty for disambiguation
            (0.35 if looks_generic else 0)    # Penalty for generic/category-like pages
        )
        
        print(f"    Evaluating: {page.get('title', 'Unknown')} (Score: {composite_score:.3f})")
        
        if composite_score > best_score and composite_score > 0.2:  # Lower threshold
            best_score = composite_score
            best_match = page
    
    return best_match

def generate_search_variants(disease_name):
    """
    Generate different search variants for a disease name with improved core term extraction
    """
    # Always try full title first
    # start from cleaned title
    cleaned_full = clean_disease_name(disease_name)
    variants = [cleaned_full]
    
    # Extract core medical terms (phrases preserved)
    core_terms = extract_key_medical_terms(disease_name)
    
    # Add core terms as standalone searches (phrases before single words)
    for term in core_terms:
        if len(term) > 3:  # Avoid very short terms
            variants.append(term)
    
    # Add combinations of core terms
    if len(core_terms) >= 2:
        variants.append(' '.join(core_terms[:2]))
    
    # Add variant without common suffixes
    base_name = re.sub(r'\s+(disease|syndrome|disorder|disorders|condition|illness)$', '', cleaned_full, flags=re.IGNORECASE)
    if base_name != cleaned_full:
        variants.append(base_name)
    
    # Add variant with medical suffixes if not present
    if not re.search(r'\b(disease|syndrome|disorder|disorders|condition|illness)\b', cleaned_full, re.IGNORECASE):
        # Try with the most common medical suffixes
        for suffix in ['disease', 'syndrome', 'disorder']:
            variants.append(f"{core_terms[0]} {suffix}" if core_terms else f"{cleaned_full} {suffix}")
    
    # Add variant with simplified punctuation
    simplified = re.sub(r'[^\w\s]', '', cleaned_full)
    if simplified != cleaned_full:
        variants.append(simplified)
    
    # Remove duplicates and sort by specificity (prefer phrases and longer, but keep original order priority)
    seen = set()
    unique_variants = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            unique_variants.append(v)
    # stable prioritize phrases before single-word tokens after the first element
    first = unique_variants[:1]
    rest = unique_variants[1:]
    rest.sort(key=lambda x: (1 if ' ' not in x else 0, -len(x)))
    unique_variants = first + rest

    return unique_variants

def fetch_symptoms_wikipedia(disease):
    """
    Fetch symptoms from Wikipedia API with improved core term matching
    """
    if not is_valid_disease_name(disease):
        return "Skipped - Not a specific disease"
    
    clean_disease = clean_disease_name(disease)
    search_variants = generate_search_variants(clean_disease)
    
    print(f"  Generated search variants: {search_variants}")
    
    headers = {'User-Agent': 'Medical Research Tool 1.0'}
    
    for idx, variant in enumerate(search_variants):
        try:
            print(f"  Trying variant: '{variant}'")
            
            # First try exact page match
            exact_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{variant.replace(' ', '_')}"
            exact_response = requests.get(exact_url, headers=headers, timeout=10)
            
            if exact_response.status_code == 200:
                data = exact_response.json()
                # Detect disambiguation or generic pages on the first (full-title) attempt
                page_type = data.get('type', '').lower()
                title_l = (data.get('title') or '').lower()
                desc_l = (data.get('description') or '').lower()
                generic_flags = ['disambiguation', 'category:', 'list of', 'traditional medicine', 'tm2', 'unspecified', 'other specified']
                looks_generic = (
                    page_type == 'disambiguation' or
                    any(g in title_l for g in generic_flags) or
                    any(g in desc_l for g in generic_flags)
                )
                if 'extract' in data and data['extract'] and len(data['extract']) > 50 and not looks_generic:
                    extract = data['extract']
                    print(f"  ✓ Found exact match: {data.get('title', variant)}")
                    return process_wikipedia_extract(extract, data.get('title', variant))
                # If this was the full-title attempt and it looks generic, fall through to next variant
            
            # If exact match fails, try search
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/search/?q={variant}"
            search_response = requests.get(search_url, headers=headers, timeout=10)
            
            if search_response.status_code == 200:
                search_data = search_response.json()
                best_match = find_best_wikipedia_match(variant, search_data)
                
                if best_match:
                    match_title = best_match.get('key', best_match.get('title', ''))
                    print(f"  ✓ Found best match: {best_match.get('title', match_title)}")
                    
                    # Get the content of the best match
                    match_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{match_title}"
                    match_response = requests.get(match_url, headers=headers, timeout=10)
                    
                    if match_response.status_code == 200:
                        match_data = match_response.json()
                        extract = match_data.get('extract', '')
                        # Skip generic/disambiguation result when using the full-title attempt
                        mt_title_l = (match_data.get('title') or '').lower()
                        mt_desc_l = (match_data.get('description') or '').lower()
                        mt_type = (match_data.get('type') or '').lower()
                        generic_flags = ['disambiguation', 'category:', 'list of', 'traditional medicine', 'tm2', 'unspecified', 'other specified']
                        mt_generic = (
                            mt_type == 'disambiguation' or
                            any(g in mt_title_l for g in generic_flags) or
                            any(g in mt_desc_l for g in generic_flags)
                        )
                        if extract and len(extract) > 50 and not (idx == 0 and mt_generic):
                            return process_wikipedia_extract(extract, match_data.get('title', match_title))
            
        except Exception as e:
            print(f"  ⚠️ Error with variant '{variant}': {str(e)}")
            continue
    
    return "No Wikipedia information found"

def process_wikipedia_extract(extract, title=""):
    """
    Process Wikipedia extract to focus on symptom-related information
    """
    if not extract or len(extract) < 50:
        return "No sufficient Wikipedia information found"
    
    # Look for symptom-related content
    symptom_keywords = [
        'symptom', 'symptoms', 'sign', 'signs', 'present', 'presents', 'include', 'includes',
        'characterized by', 'manifests', 'manifest', 'features', 'clinical', 'associated with',
        'causes', 'experience', 'feeling', 'sensation', 'episodes'
    ]
    
    sentences = re.split(r'[.!?]+', extract)
    relevant_sentences = []
    general_info = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 20:
            if any(keyword in sentence.lower() for keyword in symptom_keywords):
                relevant_sentences.append(sentence)
            else:
                general_info.append(sentence)
    
    # Prioritize symptom-related sentences, but include general info if no symptoms found
    final_sentences = relevant_sentences[:3] if relevant_sentences else general_info[:2]
    
    if final_sentences:
        result = '. '.join(final_sentences)
        if not result.endswith('.'):
            result += '.'
        # Add source title
        source_info = f" (Source: {title})" if title else ""
        result = result + source_info
        return result[:1500] + "..." if len(result) > 1500 else result
    else:
        # Fallback to first part of extract
        source_info = f" (Source: {title})" if title else ""
        result = extract[:500] + source_info
        return result + "..." if len(result) > 500 else result

def fetch_symptoms_pubmed(disease):
    """
    Alternative: Try to get information from PubMed abstracts
    """
    clean_disease = clean_disease_name(disease)
    core_terms = extract_key_medical_terms(clean_disease)
    
    try:
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        
        # Try multiple search strategies including core terms
        search_terms = [
            f'"{clean_disease}" AND (symptoms OR clinical OR manifestation)',
            f'{clean_disease} symptoms',
        ]
        
        # Add core term searches
        if core_terms:
            search_terms.extend([
                f'{core_terms[0]} symptoms',
                f'{core_terms[0]} clinical features'
            ])
        
        for search_term in search_terms:
            search_url = f"{base_url}esearch.fcgi?db=pubmed&term={search_term}&retmode=json&retmax=5"
            
            response = requests.get(search_url, timeout=10)
            if response.status_code == 200:
                search_data = response.json()
                ids = search_data.get('esearchresult', {}).get('idlist', [])
                
                if ids:
                    summary_url = f"{base_url}esummary.fcgi?db=pubmed&id={','.join(ids[:3])}&retmode=json"
                    summary_response = requests.get(summary_url, timeout=10)
                    
                    if summary_response.status_code == 200:
                        summary_data = summary_response.json()
                        relevant_titles = []
                        
                        for uid in ids[:3]:
                            if uid in summary_data.get('result', {}):
                                title = summary_data['result'][uid].get('title', '')
                                relevance_keywords = ['symptom', 'clinical', 'manifestation', 'feature', 'presentation']
                                # Only accept if clearly symptom/clinical-related; otherwise fall back to tokenized variants
                                if any(keyword in title.lower() for keyword in relevance_keywords):
                                    relevant_titles.append(title)
                        
                        if relevant_titles:
                            return "PubMed findings: " + " | ".join(relevant_titles[:2])
            
            time.sleep(0.5)
        
        return "No relevant PubMed information found"
        
    except Exception as e:
        return f"PubMed Error: {str(e)}"

def fetch_symptoms_combined(disease):
    """
    Try multiple sources with improved core term extraction
    """
    clean_name = clean_disease_name(disease)
    core_terms = extract_key_medical_terms(clean_name)
    
    print(f"🔍 Searching for: {clean_name}")
    print(f"  Core medical terms: {core_terms}")
    
    # Try Wikipedia first (full title first, tokenized only if generic)
    wiki_result = fetch_symptoms_wikipedia(disease)
    
    if wiki_result and "No Wikipedia information found" not in wiki_result and "Error" not in wiki_result:
        return wiki_result
    
    # If Wikipedia fails, try PubMed (also full title first in its internal strategies)
    print("  Wikipedia search unsuccessful, trying PubMed...")
    pubmed_result = fetch_symptoms_pubmed(disease)
    
    if pubmed_result and "No relevant PubMed information found" not in pubmed_result and "Error" not in pubmed_result:
        return pubmed_result
    
    return "No reliable medical information found from available sources"

def main():
    print("🔬 Medical Symptom Fetcher - Enhanced Medical Term Recognition")
    print("Improvements: Better medical classification handling, fixed 'other specified' cases")
    print("Sources: Wikipedia Medical Articles, PubMed Database")
    print("-" * 80)
    
    # Test with problematic cases first
    test_cases = [
        "Vertigo and giddiness disorder",
        "Other specified headache disorders", 
        "Unspecified mood disorder",
        "Primary headache disorders"
    ]
    
    print("🧪 Testing improved medical term extraction...")
    for test_case in test_cases:
        core_terms = extract_key_medical_terms(test_case)
        print(f"  '{test_case}' -> Core terms: {core_terms}")
    
    print("\n🧪 Testing one full search...")
    test_result = fetch_symptoms_combined("Other specified headache disorders")
    print(f"Test result: {test_result[:200]}...")
    print("-" * 80)
    
    # --- Rest of the main function remains the same ---
    file_path = r"/Users/hridayshah/SIH2025/final.xlsx"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    try:
        df = pd.read_excel(file_path)
        print(f"✅ Successfully loaded {len(df)} rows from Excel file")
        print(f"Columns available: {list(df.columns)}")
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return
    
    required_cols = ["Code", "Title"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"❌ Missing required columns: {missing_cols}")
        return
    
    # Preview improvements
    print("\nTesting improved matching on first 5 entries:")
    print(f"{'Index':<5} {'Original Name':<40} {'Core Terms':<20} {'Valid'}")
    print("-" * 80)
    
    for i in range(min(5, len(df))):
        title = df.iloc[i]["Title"] if not pd.isna(df.iloc[i]["Title"]) else "N/A"
        valid = "✓" if is_valid_disease_name(title) else "✗"
        
        if is_valid_disease_name(title):
            clean_title = clean_disease_name(title)
            core_terms = extract_key_medical_terms(clean_title)
            core_str = ', '.join(core_terms) if core_terms else "None"
        else:
            core_str = "SKIPPED"
        
        print(f"{i+1:<5} {title[:39]:<40} {core_str[:19]:<20} {valid}")
    
    valid_mask = df["Title"].apply(is_valid_disease_name)
    valid_diseases = df[valid_mask]
    print(f"\nFound {len(valid_diseases)} valid diseases out of {len(df)} total entries")
    
    output_path = r"/Users/hridayshah/SIH2025/final_final_symptoms.xlsx"
    
    print(f"\n📋 Results will be saved to: {output_path}")
    print("🔍 New Improvements:")
    print("  ✓ Core medical term extraction (handles 'Vertigo and giddiness' -> 'Vertigo')")
    print("  ✓ Better search variant generation")
    print("  ✓ Enhanced similarity scoring")
    print("  ✓ Improved medical relevance detection")
    
    response = input(f"\nDo you want to continue processing {len(valid_diseases)} valid diseases? (y/n): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Continue with the same processing logic...
    results_df = pd.DataFrame(columns=["Code", "Disease_Name", "Symptoms", "Search_Quality", "Core_Terms"])
    
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        results_df.to_excel(output_path, index=False)
        print(f"📝 Created initial file: {output_path}")
    except Exception as e:
        print(f"❌ Error creating initial file: {e}")
        return
    
    processed_count = 0
    successful_searches = 0
    
    for i, row in df.iterrows():
        code = row["Code"] if not pd.isna(row["Code"]) else ""
        disease = row["Title"]
        
        print(f"\n{'='*60}")
        print(f"Processing {i+1}/{len(df)}: {disease}")
        
        if pd.isna(disease):
            new_row = {
                "Code": code,
                "Disease_Name": "No disease name",
                "Symptoms": "No disease name provided",
                "Search_Quality": "N/A",
                "Core_Terms": ""
            }
        elif not is_valid_disease_name(disease):
            new_row = {
                "Code": code,
                "Disease_Name": disease,
                "Symptoms": "Skipped - Not a specific disease",
                "Search_Quality": "Skipped",
                "Core_Terms": ""
            }
        else:
            clean_name = clean_disease_name(disease)
            core_terms = extract_key_medical_terms(clean_name)
            symptoms = fetch_symptoms_combined(disease)
            
            # Determine search quality
            if "No reliable medical information found" in symptoms:
                quality = "No match"
            elif "PubMed" in symptoms:
                quality = "PubMed match"
            elif "Source:" in symptoms:
                quality = "Wikipedia match"
            elif len(symptoms) > 100:
                quality = "Good match"
            else:
                quality = "Partial match"
            
            new_row = {
                "Code": code,
                "Disease_Name": clean_name,
                "Symptoms": symptoms,
                "Search_Quality": quality,
                "Core_Terms": ', '.join(core_terms)
            }
            
            processed_count += 1
            if quality != "No match":
                successful_searches += 1
            
        results_df = pd.concat([results_df, pd.DataFrame([new_row])], ignore_index=True)
        
        try:
            results_df.to_excel(output_path, index=False)
            print(f"💾 Saved entry {i+1}/{len(df)} | Quality: {new_row.get('Search_Quality', 'N/A')}")
        except Exception as e:
            print(f"⚠️ Warning: Could not save after entry {i+1}: {e}")
        
        if is_valid_disease_name(disease):
            time.sleep(1.5)  # Slightly faster

    # Final summary
    try:        
        print(f"\n{'='*60}")
        print("🎉 PROCESSING COMPLETE WITH IMPROVED MATCHING!")
        print(f"✅ Results saved to {output_path}")
        
        print(f"\n📊 Summary Statistics:")
        print(f"  Total entries processed: {len(results_df)}")
        print(f"  Valid diseases searched: {processed_count}")
        print(f"  Successful symptom matches: {successful_searches}")
        print(f"  Success rate: {(successful_searches/processed_count*100):.1f}%" if processed_count > 0 else "N/A")
        
        quality_counts = results_df['Search_Quality'].value_counts()
        print(f"\n🎯 Search Quality Breakdown:")
        for quality, count in quality_counts.items():
            print(f"  {quality}: {count}")
        
        successful_df = results_df[results_df['Search_Quality'].isin(['Wikipedia match', 'Good match', 'PubMed match'])]
        if len(successful_df) > 0:
            print(f"\nSample of successful matches:")
            print(successful_df[['Disease_Name', 'Core_Terms', 'Search_Quality']].head().to_string(index=False))
        
    except Exception as e:
        print(f"❌ Error in final summary: {e}")
        print(f"But the file has been saved incrementally at: {output_path}")

if __name__ == "__main__":
    main()