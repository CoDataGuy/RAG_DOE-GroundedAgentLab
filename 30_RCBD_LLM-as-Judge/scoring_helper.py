def create_scoring_template(input_csv, output_csv="../Output/scoring_template_CRD.csv"):
    """
    Create simplified CSV for manual scoring review.
    """
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df = pd.read_csv(input_csv)
    df_success = df[df['status'] == 'SUCCESS'].copy()
    
    scoring_df = df_success[[
        'run_id', 'replicate', 'question_number', 'question_type',
        'question_text', 'answer', 'agent_thinking', 'retrieved_chunks'
    ]].copy()
    
    scoring_df['C1_correctness'] = ''
    scoring_df['C2_coverage'] = ''
    scoring_df['C3_citation_presence'] = ''
    scoring_df['C4_citation_valid'] = ''
    scoring_df['C5_clarity'] = ''
    scoring_df['scoring_notes'] = ''
    
    scoring_df.to_csv(output_csv, index=False)
    print(f"✅ Scoring template: {output_csv}")
    print(f"   {len(scoring_df)} responses to score")


def merge_scores(experiment_csv, scored_csv, output_csv="../Output/final_CRD_with_rgs.csv"):
    """
    Merge scored C1-C5 back and calculate RGS.
    RGS = C1 × (C2 + C3 + C4 + C5) / 4
    """
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_exp = pd.read_csv(experiment_csv)
    df_scored = pd.read_csv(scored_csv)
    
    df_scored['RGS'] = (
        df_scored['C1_correctness'] *
        (df_scored['C2_coverage'] + df_scored['C3_citation_presence'] +
         df_scored['C4_citation_valid'] + df_scored['C5_clarity']) / 4
    )
    
    df_merged = df_exp.merge(
        df_scored[['run_id', 'C1_correctness', 'C2_coverage',
                   'C3_citation_presence', 'C4_citation_valid',
                   'C5_clarity', 'RGS', 'scoring_notes']],
        on='run_id', how='left', suffixes=('', '_scored')
    )
    
    for col in ['C1_correctness', 'C2_coverage', 'C3_citation_presence',
                'C4_citation_valid', 'C5_clarity', 'RGS', 'scoring_notes']:
        if f'{col}_scored' in df_merged.columns:
            df_merged[col] = df_merged[f'{col}_scored'].combine_first(df_merged[col])
            df_merged.drop(f'{col}_scored', axis=1, inplace=True)
    
    df_merged.to_csv(output_csv, index=False)
    print(f"✅ Final CSV: {output_csv}")
    print(f"\nRGS Statistics by Question Type:")
    print(df_merged[df_merged['status']=='SUCCESS'].groupby('question_type')['RGS'].describe())
    print(f"\nRGS Statistics by Replicate:")
    print(df_merged[df_merged['status']=='SUCCESS'].groupby('replicate')['RGS'].describe())

print("✓ Post-experiment helpers defined")