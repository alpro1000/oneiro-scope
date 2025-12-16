import pandas as pd


def test_dreamy_swisseph_integration(pipeline):
    df: pd.DataFrame = pipeline.run_pipeline(save=False)
    assert "dreamy_embedding" in df.columns
    assert "lunar_phase" in df.columns
    assert all(df["lunar_phase"].between(0, 1))
    assert df["dreamy_embedding"].apply(lambda emb: isinstance(emb, list)).all()
