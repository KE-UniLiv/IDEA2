import notion_utils
import questionary
import os



if __name__ == "__main__":
    os.system("CLS")
    metric = questionary.select("Choose something to evaluate:",
                       choices=["Percentage of CQs Answered by Annotators", 
                                "Number of Comments Left By Annotators", 
                                "Total Accepted CQs In An Iteration",
                                "Negative CQ Metrics"]).ask()

    if metric == "Total Accepted CQs In An Iteration":
        iteration = questionary.text("Enter the iteration number you would like to query:").ask()
        notion_utils.get_metrics_by_iteration(int(iteration))

    if metric == "Percentage of CQs Answered by Annotators":
        notion_utils.get_cq_metrics_by_user()

    if metric == "Number of Comments Left By Annotators":
        notion_utils.pull_comments()

    if metric == "Negative CQ Metrics":
        iteration = questionary.text("Enter the iteration number you would like to query:").ask()
        notion_utils.get_negative_cq_metrics(int(iteration))

