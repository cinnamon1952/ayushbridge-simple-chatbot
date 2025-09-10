import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from scipy.spatial.distance import cdist
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def analyze_excel_structure(file_path):
    """Analyze the structure of an Excel file"""
    try:
        df = pd.read_excel(file_path)
        print(f"\nFile: {file_path}")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"First few rows:")
        print(df.head())
        return df
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def create_3d_features(texts):
    """Create 3D features from text using TF-IDF and PCA"""
    # Vectorize text
    vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
    X_tfidf = vectorizer.fit_transform(texts)
    
    # Reduce to 3D using PCA
    pca = PCA(n_components=3, random_state=42)
    X_3d = pca.fit_transform(X_tfidf.toarray())
    
    return X_3d, vectorizer, pca

def calculate_euclidean_distances(points1, points2):
    """Calculate Euclidean distances between all pairs of points from two datasets"""
    distances = cdist(points1, points2, metric='euclidean')
    return distances

def find_closest_matches(distances, threshold=None):
    """Find closest matches between datasets"""
    closest_indices = np.argmin(distances, axis=1)
    min_distances = np.min(distances, axis=1)
    
    if threshold:
        valid_matches = min_distances <= threshold
        return closest_indices[valid_matches], min_distances[valid_matches], valid_matches
    else:
        return closest_indices, min_distances, np.ones(len(closest_indices), dtype=bool)

# Load and analyze the Excel files
print("Analyzing Excel files...")
final_df = analyze_excel_structure("/Users/hridayshah/SIH2025/final_symptoms.xlsx")
defs_df = analyze_excel_structure("/Users/hridayshah/SIH2025/combined_definitions.xlsx")

print("Files loaded successfully!")

if final_df is not None and defs_df is not None:
    # Extract relevant columns
    # For final_symptoms.xlsx: Code and Disease_Name (not Title)
    final_codes = final_df["Code"].dropna().astype(str).tolist() if "Code" in final_df.columns else []
    final_titles = final_df["Disease_Name"].dropna().astype(str).tolist() if "Disease_Name" in final_df.columns else []
    
    # Filter out skipped entries and empty titles
    valid_indices = []
    valid_codes = []
    valid_titles = []
    
    for i, (code, title) in enumerate(zip(final_codes, final_titles)):
        if (title and 
            title.strip() != "" and 
            "Skipped" not in title and 
            "Not a specific disease" not in title and
            not title.startswith("-")):
            valid_indices.append(i)
            valid_codes.append(code)
            valid_titles.append(title)
    
    final_codes = valid_codes
    final_titles = valid_titles
    
    # For combined_definitions.xlsx: NAMC_CODE, NAMC_TERM2, NUMC_CODE, Definition
    # Don't drop NaN values, handle them in the loop
    defs_namc = defs_df["NAMC_CODE"].fillna("").astype(str).tolist() if "NAMC_CODE" in defs_df.columns else []
    defs_namc2 = defs_df["NAMC_TERM2"].fillna("").astype(str).tolist() if "NAMC_TERM2" in defs_df.columns else []
    defs_numc = defs_df["NUMC_CODE"].fillna("").astype(str).tolist() if "NUMC_CODE" in defs_df.columns else []
    defs_definitions = defs_df["Definition"].fillna("").astype(str).tolist() if "Definition" in defs_df.columns else []
    
    print(f"\nData extracted:")
    print(f"Final codes: {len(final_codes)}")
    print(f"Final titles: {len(final_titles)}")
    print(f"Definitions NAMC_CODE: {len(defs_namc)}")
    print(f"Definitions NAMC_TERM2: {len(defs_namc2)}")
    print(f"Definitions NUMC_CODE: {len(defs_numc)}")
    print(f"Definitions: {len(defs_definitions)}")
    
    # Combine all text data for clustering
    all_texts = []
    text_sources = []
    text_metadata = []
    
    # Add final data
    for i, (code, title) in enumerate(zip(final_codes, final_titles)):
        combined_text = f"{code} {title}"
        all_texts.append(combined_text)
        text_sources.append("final")
        text_metadata.append({"type": "final", "code": code, "title": title, "index": i})
    
    # Add definitions data - be more lenient with filtering
    definitions_added = 0
    for i, (namc, namc2, numc, definition) in enumerate(zip(defs_namc, defs_namc2, defs_numc, defs_definitions)):
        # Only skip if ALL fields are truly empty
        has_content = False
        if definition and definition.strip() != "" and definition != "nan":
            has_content = True
        if namc and namc.strip() != "" and namc != "nan":
            has_content = True
        if numc and numc.strip() != "" and numc != "nan":
            has_content = True
            
        if not has_content:
            continue
            
        combined_text = f"{namc} {namc2} {numc} {definition}"
        all_texts.append(combined_text)
        text_sources.append("definitions")
        text_metadata.append({
            "type": "definitions", 
            "namc": namc, 
            "namc2": namc2, 
            "numc": numc, 
            "definition": definition, 
            "index": i
        })
        definitions_added += 1
    
    print(f"Definitions entries added: {definitions_added}")
    
    if len(all_texts) < 2:
        print("Not enough data for clustering")
        print(f"Valid final entries: {len(final_codes)}")
        print(f"Valid definitions entries: {len(defs_definitions)}")
    else:
        # Create 3D features
        print("\nCreating 3D features...")
        X_3d, vectorizer, pca = create_3d_features(all_texts)
        
        # Determine optimal number of clusters
        n_clusters = min(8, max(2, len(all_texts) // 5))
        
        # Perform 3D K-means clustering
        print(f"Performing 3D K-means clustering with {n_clusters} clusters...")
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X_3d)
        
        # Separate points by dataset
        final_indices = [i for i, source in enumerate(text_sources) if source == "final"]
        defs_indices = [i for i, source in enumerate(text_sources) if source == "definitions"]
        
        print(f"Final indices: {len(final_indices)}, Definitions indices: {len(defs_indices)}")
        
        if len(final_indices) == 0 or len(defs_indices) == 0:
            print("Error: One or both datasets are empty after filtering")
            print(f"Final dataset size: {len(final_indices)}")
            print(f"Definitions dataset size: {len(defs_indices)}")
        else:
            final_points = X_3d[final_indices]
            defs_points = X_3d[defs_indices]
            
            # Calculate Euclidean distances between opposite datasets
            print("Calculating Euclidean distances...")
            distances = calculate_euclidean_distances(final_points, defs_points)
            
            # Find closest matches
            closest_defs_indices, min_distances, valid_matches = find_closest_matches(distances)
            
            # Create comprehensive results
            results = []
            
            # Add final dataset results
            for i, final_idx in enumerate(final_indices):
                result = {
                    "dataset": "final",
                    "cluster": cluster_labels[final_idx],
                    "x_coord": X_3d[final_idx, 0],
                    "y_coord": X_3d[final_idx, 1],
                    "z_coord": X_3d[final_idx, 2],
                    "text": all_texts[final_idx],
                    "metadata": text_metadata[final_idx]
                }
                
                # Add distance information
                if i < len(closest_defs_indices):
                    closest_def_idx = defs_indices[closest_defs_indices[i]]
                    result.update({
                        "closest_definitions_index": closest_defs_indices[i],
                        "euclidean_distance": min_distances[i],
                        "closest_definitions_text": all_texts[closest_def_idx],
                        "closest_definitions_metadata": text_metadata[closest_def_idx]
                    })
                
                results.append(result)
            
            # Add definitions dataset results
            for i, def_idx in enumerate(defs_indices):
                result = {
                    "dataset": "definitions",
                    "cluster": cluster_labels[def_idx],
                    "x_coord": X_3d[def_idx, 0],
                    "y_coord": X_3d[def_idx, 1],
                    "z_coord": X_3d[def_idx, 2],
                    "text": all_texts[def_idx],
                    "metadata": text_metadata[def_idx]
                }
                
                # Find closest final point
                final_distances = distances[:, i]
                closest_final_idx = np.argmin(final_distances)
                result.update({
                    "closest_final_index": closest_final_idx,
                    "euclidean_distance": final_distances[closest_final_idx],
                    "closest_final_text": all_texts[final_indices[closest_final_idx]],
                    "closest_final_metadata": text_metadata[final_indices[closest_final_idx]]
                })
                
                results.append(result)
            
            # Create results DataFrame
            results_df = pd.DataFrame(results)
            
            # Save to Excel
            output_path = "clustering_results_3d.xlsx"
            results_df.to_excel(output_path, index=False)
            print(f"\nResults saved to {output_path}")
            
            # Create 3D visualization
            print("Creating 3D visualization...")
            fig = plt.figure(figsize=(12, 10))
            ax = fig.add_subplot(111, projection='3d')
            
            # Add final points
            final_mask = results_df["dataset"] == "final"
            final_points = results_df[final_mask]
            scatter1 = ax.scatter(final_points["x_coord"], 
                                 final_points["y_coord"], 
                                 final_points["z_coord"],
                                 c=final_points["cluster"], 
                                 cmap='viridis', 
                                 s=50, 
                                 alpha=0.7,
                                 label='Final Dataset')
            
            # Add definitions points
            defs_mask = results_df["dataset"] == "definitions"
            defs_points = results_df[defs_mask]
            scatter2 = ax.scatter(defs_points["x_coord"], 
                                 defs_points["y_coord"], 
                                 defs_points["z_coord"],
                                 c=defs_points["cluster"], 
                                 cmap='plasma', 
                                 s=50, 
                                 alpha=0.7,
                                 marker='^',
                                 label='Definitions Dataset')
            
            ax.set_xlabel('PC1')
            ax.set_ylabel('PC2')
            ax.set_zlabel('PC3')
            ax.set_title('3D K-means Clustering: Final vs Definitions Datasets')
            ax.legend()
            
            plt.tight_layout()
            plt.savefig("3d_clustering_visualization.png", dpi=300, bbox_inches='tight')
            print("3D visualization saved to 3d_clustering_visualization.png")
            
            # Print summary statistics
            print(f"\nSummary:")
            print(f"Total points: {len(all_texts)}")
            print(f"Final dataset points: {len(final_indices)}")
            print(f"Definitions dataset points: {len(defs_indices)}")
            print(f"Number of clusters: {n_clusters}")
            print(f"Average distance between closest matches: {np.mean(min_distances):.4f}")
            print(f"Min distance: {np.min(min_distances):.4f}")
            print(f"Max distance: {np.max(min_distances):.4f}")
            
            # Show cluster distribution
            print(f"\nCluster distribution:")
            cluster_counts = pd.Series(cluster_labels).value_counts().sort_index()
            for cluster, count in cluster_counts.items():
                print(f"Cluster {cluster}: {count} points")

else:
    print("Could not load one or both Excel files. Please check the file paths and structure.")