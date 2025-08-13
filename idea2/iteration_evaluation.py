import notion_utils
import questionary
import os



if __name__ == "__main__":
    os.system("CLS")
    metric = questionary.select("Choose something to evaluate:",
                       choices=["Percentage of CQs answered by Annotators", "Number of comments left by annotators"]).ask()

    if metric == "Percentage of CQs answered by Annotators":
        notion_utils.get_cq_metrics_by_user()

    if metric == "Number of comments left":
        notion_utils.get_comments_by_user()