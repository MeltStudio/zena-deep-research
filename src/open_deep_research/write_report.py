"""Report writing nodes for the Deep Research agent."""

import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
    filter_messages,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from open_deep_research.configuration import Configuration
from open_deep_research.conts import documents_source1
from open_deep_research.ingest_initial_documents import ingest_documents_to_store
from open_deep_research.prompts import (
    compress_report_research_system_prompt,
    compress_research_simple_human_message,
    create_report_plan_prompt,
    report_research_supervisor_prompt,
    report_research_system_prompt,
    write_report_section_prompt,
)
from open_deep_research.state import (
    AgentState,
    ConductReportResearch,
    ReportPlan,
    ReportResearchComplete,
    ReportResearcherState,
    ReportSupervisorState,
    ResearcherOutputState,
)
from open_deep_research.utils import (
    execute_tool_safely,
    get_all_tools,
    get_api_key_for_model,
    get_notes_from_tool_calls,
    get_today_str,
    is_token_limit_exceeded,
    remove_up_to_last_ai_message,
    search_research_findings,
    think_tool,
)


# Initialize a configurable model for report writing
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def write_report_plan(
    state: AgentState, config: RunnableConfig
) -> Command[Literal["report_supervisor"]]:
    """Generate a detailed report plan based on the research brief and report structure.

    This function analyzes the research brief and report structure to create a comprehensive
    plan that outlines what information needs to be gathered for each section of the report.
    The plan will guide the research and writing process.

    Args:
        state: Current agent state containing research_brief and report_structure
        config: Runtime configuration with model settings

    Returns:
        State update with the report_plan and report_structure
    """
    # Step 1: Set up the report plan model
    configurable = Configuration.from_runnable_config(config)
    report_plan_model_config = {
        "model": configurable.report_plan_model,
        "max_tokens": configurable.report_plan_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.report_plan_model, config),
        "tags": ["langsmith:nostream"],
    }

    # Configure model with retry logic and model settings
    report_plan_model = (
        configurable_model.with_structured_output(ReportPlan)
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(report_plan_model_config)
    )

    # Step 2: Get the research brief and report structure from state
    messages = state.get("messages", "")
    research_brief = messages[-1].text
    #TODO: this its hardcoded for now, but we should make it dynamic based on the configuration.
    report_structure = documents_source1

    # Step 3: Generate the report plan using the prompt
    prompt_content = create_report_plan_prompt.format(
        research_brief=research_brief,
        report_structure=report_structure,
        date=get_today_str(),
    )

    response = await report_plan_model.ainvoke([SystemMessage(content=prompt_content)])

    report_research_supervisor_system_prompt = report_research_supervisor_prompt.format(
        report_plan=response.report_plan,
        date=get_today_str(),
        max_report_research_iterations=configurable.max_report_research_iterations,
        max_concurrent_report_research_units=configurable.max_concurrent_report_research_units,
    )

    # Step 4: Update state and proceed to report supervisor
    return Command(
        goto="report_supervisor",
        update={
            "report_plan": response.report_plan,
            "report_supervisor_messages": {
                "type": "override",
                "value": [
                    SystemMessage(content=report_research_supervisor_system_prompt),
                    HumanMessage(content=response.report_plan),
                ],
            },
        },
    )


async def report_supervisor(
    state: ReportSupervisorState, config: RunnableConfig
) -> Command[Literal["report_supervisor_tools"]]:
    """This agent is in charge of delegating each section of the report to a report researcher.

    The supervisor analyzes the report plan and assigns each section to a report researcher.
    It can use think_tool for strategic planning, ConductReportResearch
    to delegate tasks to sub-report researchers, or ReportResearchComplete when satisfied with ONLY THE RELEVANT INFORMATION FOR EACH SECTION.

    Args:
        state: Current report supervisor state with messages and report context
        config: Runtime configuration with model settings

    Returns:
        Command to proceed to report_supervisor_tools for tool execution
    """

    # Step 1: Configure the report supervisor model
    configurable = Configuration.from_runnable_config(config)
    report_supervisor_model_config = {
        "model": configurable.report_supervisor_model,
        "max_tokens": configurable.report_supervisor_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.report_supervisor_model, config),
        "tags": ["langsmith:nostream"],
    }

    # Step 2: Configure the tools for the report supervisor
    lead_report_researcher_tools = [
        ConductReportResearch,
        ReportResearchComplete,
        think_tool,
    ]

    report_supervisor_model = (
        configurable_model.bind_tools(lead_report_researcher_tools)
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(report_supervisor_model_config)
    )

    # Step 3: Generate report supervisor response based on current context
    report_supervisor_messages = state.get("report_supervisor_messages", [])
    response = await report_supervisor_model.ainvoke(report_supervisor_messages)

    # Step 4: Update state and proceed to tool execution
    return Command(
        goto="report_supervisor_tools",
        update={
            "report_supervisor_messages": [response],
            "report_research_iterations": state.get("report_research_iterations", 0)
            + 1,
        },
    )


async def report_supervisor_tools(
    state: ReportSupervisorState, config: RunnableConfig
) -> Command[Literal["report_supervisor", "__end__"]]:
    """Execute tools called by the report supervisor, including report research delegation and strategic thinking.

    This function handles three types of report supervisor tool calls:
    1. think_tool - Strategic reflection that continues the conversation
    2. ConductReportResearch - Delegates report research tasks to sub researchers
    3. ReportResearchComplete - Signals completion of report research phase

    Args:
        state: Current report supervisor state with messages and iteration count
        config: Runtime configuration with report research limits and model settings

    Returns:
        Command to either continue report supervisor loop or end report research phase
    """
    # Step 1: Extract current state and check exit conditions
    configurable = Configuration.from_runnable_config(config)
    supervisor_messages = state.get("report_supervisor_messages", [])
    research_iterations = state.get("report_research_iterations", 0)
    most_recent_message = supervisor_messages[-1]

    # Define exit criteria for report research phase
    exceeded_allowed_iterations = (
        research_iterations > configurable.max_report_research_iterations
    )
    no_tool_calls = not most_recent_message.tool_calls
    research_complete_tool_call = any(
        tool_call["name"] == "ReportResearchComplete"
        for tool_call in most_recent_message.tool_calls
    )

    # Exit if any termination condition is met
    if exceeded_allowed_iterations or no_tool_calls or research_complete_tool_call:
        final_sketches = state.get("report_section_sketches", [])
        return Command(
            goto=END,
            update={
                "report_section_sketches": final_sketches,
                "notes": get_notes_from_tool_calls(supervisor_messages),
                "report_plan": state.get("report_plan", ""),
            },
        )

    # Step 2: Process all tool calls together (both think_tool and ConductReportResearch)
    all_tool_messages = []
    update_payload = {"report_supervisor_messages": []}

    # Handle think_tool calls (strategic reflection)
    think_tool_calls = [
        tool_call
        for tool_call in most_recent_message.tool_calls
        if tool_call["name"] == "think_tool"
    ]

    for tool_call in think_tool_calls:
        reflection_content = tool_call["args"]["reflection"]
        all_tool_messages.append(
            ToolMessage(
                content=f"Reflection recorded: {reflection_content}",
                name="think_tool",
                tool_call_id=tool_call["id"],
            )
        )

    # Handle ConductReportResearch calls (report research delegation)
    conduct_research_calls = [
        tool_call
        for tool_call in most_recent_message.tool_calls
        if tool_call["name"] == "ConductReportResearch"
    ]

    if conduct_research_calls:
        try:
            # Limit concurrent research units to prevent resource exhaustion
            allowed_conduct_research_calls = conduct_research_calls[
                : configurable.max_concurrent_report_research_units
            ]
            overflow_conduct_research_calls = conduct_research_calls[
                configurable.max_concurrent_report_research_units :
            ]

            # Execute research tasks in parallel
            report_research_tasks = [
                report_researcher_subgraph.ainvoke(
                    {
                        "report_researcher_messages": [
                            HumanMessage(content=tool_call["args"]["report_section"])
                        ],
                        "report_section": tool_call["args"]["report_section"],
                    },
                    config,
                )
                for tool_call in allowed_conduct_research_calls
            ]

            tool_results = await asyncio.gather(*report_research_tasks)

            # Create tool messages with research results
            for observation, tool_call in zip(
                tool_results, allowed_conduct_research_calls
            ):
                all_tool_messages.append(
                    ToolMessage(
                        content=observation.get(
                            "report_section_sketch",
                            "Error synthesizing report section: Maximum retries exceeded",
                        ),
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                )

            # Handle overflow research calls with error messages
            for overflow_call in overflow_conduct_research_calls:
                all_tool_messages.append(
                    ToolMessage(
                        content=f"Error: Did not run this research as you have already exceeded the maximum number of concurrent research units. Please try again with {configurable.max_concurrent_report_research_units} or fewer research units.",
                        name="ConductReportResearch",
                        tool_call_id=overflow_call["id"],
                    )
                )

            # Aggregate raw notes from all research results
            raw_notes_concat = "\n".join(
                [
                    "\n".join(observation.get("raw_notes", []))
                    for observation in tool_results
                ]
            )

            if raw_notes_concat:
                update_payload["raw_notes"] = [raw_notes_concat]

            # Aggregate report section sketches from all research results
            report_section_sketches = [
                observation.get("report_section_sketch", "")
                for observation in tool_results
                if observation.get("report_section_sketch")
            ]

            if report_section_sketches:
                update_payload["report_section_sketches"] = report_section_sketches

        except Exception as e:
            # Handle research execution errors
            if is_token_limit_exceeded(e, configurable.report_researcher_model) or True:
                # Token limit exceeded or other error - end research phase
                return Command(
                    goto=END,
                    update={
                        "report_section_sketches": state.get("report_section_sketches", []),
                        "notes": get_notes_from_tool_calls(supervisor_messages),
                        "report_plan": state.get("report_plan", ""),
                    },
                )

    # Step 3: Return command with all tool results
    update_payload["report_supervisor_messages"] = all_tool_messages
    return Command(goto="report_supervisor", update=update_payload)


async def report_researcher(
    state: ReportResearcherState, config: RunnableConfig
) -> Command[Literal["report_researcher_tools"]]:
    """Individual researcher that conducts focused research on specific report sections.

    This researcher is given a specific research topic by the supervisor and uses
    available tools (search, think_tool, search_internal_documents) to gather comprehensive information.
    It can use think_tool for strategic planning between searches.

    Args:
        state: Current researcher state with messages and report section context
        config: Runtime configuration with model settings and tool availability

    Returns:
        Command to proceed to report_researcher_tools for tool execution
    """
    # Step 1: Load configuration and validate tool availability
    configurable = Configuration.from_runnable_config(config)
    report_researcher_messages = state.get("report_researcher_messages", [])

    # Get all available report researcher tools (think_tool, search, MCP tools)
    tools = await get_all_tools(config)
    if len(tools) == 0:
        raise ValueError(
            "No tools found to conduct report research: Please configure either your "
            "search API or add MCP tools to your configuration."
        )

    # Step 2: Configure the researcher model with tools
    report_researcher_model_config = {
        "model": configurable.report_researcher_model,
        "max_tokens": configurable.report_researcher_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.report_researcher_model, config),
        "tags": ["langsmith:nostream"],
    }

    # Prepare system prompt
    researcher_prompt = report_research_system_prompt.format(date=get_today_str())

    # Configure model with tools, retry logic, and settings
    research_model = (
        configurable_model.bind_tools(tools)
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(report_researcher_model_config)
    )

    # Step 3: Generate researcher response with system context
    messages = [SystemMessage(content=researcher_prompt)] + report_researcher_messages
    response = await research_model.ainvoke(messages)

    # Step 4: Update state and proceed to tool execution
    return Command(
        goto="report_researcher_tools",
        update={
            "report_researcher_messages": [response],
            "tool_call_iterations": state.get("tool_call_iterations", 0) + 1,
        },
    )


async def report_researcher_tools(
    state: ReportResearcherState, config: RunnableConfig
) -> Command[Literal["report_researcher", "compress_report_research"]]:
    """Execute tools called by the researcher, including search tools and strategic thinking.

    This function handles various types of report researcher tool calls:
    1. think_tool - Strategic reflection that continues the conversation
    2. search_research_findings - Searches for relevant information from previously embedded research findings

    Args:
        state: Current report researcher state with messages and iteration count
        config: Runtime configuration with report research limits and tool settings

    Returns:
        Command to either continue research loop or proceed to compression
    """
    # Step 1: Extract current state and check early exit conditions
    configurable = Configuration.from_runnable_config(config)
    report_researcher_messages = state.get("report_researcher_messages", [])
    most_recent_message = report_researcher_messages[-1]

    # Early exit if no tool calls were made (including native web search)
    has_tool_calls = bool(most_recent_message.tool_calls)

    if not has_tool_calls:
        return Command(goto="compress_report_research")

    # Step 2: Handle tool calls - FIX: Get tools dynamically like in deep_researcher.py
    tools = await get_all_tools(config)
    tools_by_name = {
        tool.name if hasattr(tool, "name") else tool.get("name", "web_search"): tool 
        for tool in tools
    }

    # Execute all tool calls in parallel
    tool_calls = most_recent_message.tool_calls
    tool_execution_tasks = [
        execute_tool_safely(tools_by_name[tool_call["name"]], tool_call["args"], config)
        for tool_call in tool_calls
    ]
    observations = await asyncio.gather(*tool_execution_tasks)

    # Create tool messages from execution results
    tool_outputs = [
        ToolMessage(
            content=observation, name=tool_call["name"], tool_call_id=tool_call["id"]
        )
        for observation, tool_call in zip(observations, tool_calls)
    ]

    # Step 3: Check late exit conditions (after processing tools)
    exceeded_iterations = (
        state.get("tool_call_iterations", 0) >= configurable.max_report_research_react_tool_calls
    )
    research_complete_called = any(
        tool_call["name"] == "ReportResearchComplete"
        for tool_call in most_recent_message.tool_calls
    )

    if exceeded_iterations or research_complete_called:
        # End research and proceed to compression
        return Command(
            goto="compress_report_research",
            update={"report_researcher_messages": tool_outputs},
        )

    # Continue research loop with tool results
    return Command(
        goto="report_researcher", update={"report_researcher_messages": tool_outputs}
    )


async def compress_report_research(
    state: ReportResearcherState, config: RunnableConfig
) -> ResearcherOutputState:
    """Compress and synthesize research findings.

    This function takes all the research findings, tool outputs, and AI messages from
    a researcher's work and distills them into a clean, comprehensive summary while
    preserving all important information and findings.

    Args:
        state: Current researcher state with accumulated research messages
        config: Runtime configuration with compression model settings

    Returns:
        Dictionary containing compressed research summary and raw notes
    """
    # Step 1: Configure the compression model
    configurable = Configuration.from_runnable_config(config)
    synthesizer_model = configurable_model.with_config(
        {
            "model": configurable.compression_model,
            "max_tokens": configurable.compression_model_max_tokens,
            "api_key": get_api_key_for_model(configurable.compression_model, config),
            "tags": ["langsmith:nostream"],
        }
    )

    # Step 2: Prepare messages for compression
    report_researcher_messages = state.get("report_researcher_messages", [])

    # Add instruction to switch from research mode to compression mode
    report_researcher_messages.append(
        HumanMessage(content=compress_research_simple_human_message)
    )

    # Step 3: Attempt compression with retry logic for token limit issues
    synthesis_attempts = 0
    max_attempts = 3
    compressed_research = None
    raw_notes_content = None

    while synthesis_attempts < max_attempts:
        try:
            # Create system prompt focused on compression task
            compression_prompt = compress_report_research_system_prompt.format(
                date=get_today_str()
            )
            messages = [
                SystemMessage(content=compression_prompt)
            ] + report_researcher_messages

            # Execute compression
            response = await synthesizer_model.ainvoke(messages)

            # Extract raw notes from all tool and AI messages
            raw_notes_content = "\n".join(
                [
                    str(message.content)
                    for message in filter_messages(
                        report_researcher_messages, include_types=["tool", "ai"]
                    )
                ]
            )

            compressed_research = str(response.content)
            break

        except Exception as e:
            synthesis_attempts += 1

            # Handle token limit exceeded by removing older messages
            if is_token_limit_exceeded(e, configurable.report_researcher_model):
                report_researcher_messages = remove_up_to_last_ai_message(
                    report_researcher_messages
                )
                continue

            # For other errors, continue retrying
            continue

    # Step 4: Handle compression failure
    if compressed_research is None:
        raw_notes_content = "\n".join(
            [
                str(message.content)
                for message in filter_messages(
                    report_researcher_messages, include_types=["tool", "ai"]
                )
            ]
        )
        compressed_research = (
            "Error synthesizing report research: Maximum retries exceeded"
        )

    # Step 8: Return compression result
    return {
        "compressed_research": compressed_research,
        "raw_notes": [raw_notes_content],
    }

async def write_report_section(
    state: ReportResearcherState, config: RunnableConfig
) -> Command[Literal["__end__"]]:
    """Write a report section based on the research findings.
    
    This function takes the compressed research findings and the report section
    requirements to generate a final written section for the report.
    
    Args:
        state: Current report researcher state with compressed_research and report_section
        config: Runtime configuration with model settings
        
    Returns:
        Command to end the report researcher subgraph with the written section
    """
    # Step 1: Configure the write report section model
    configurable = Configuration.from_runnable_config(config)
    write_report_section_model_config = {
        "model": configurable.write_report_section_model,
        "max_tokens": configurable.write_report_section_model_max_tokens,
        "api_key": get_api_key_for_model(configurable.write_report_section_model, config),
        "tags": ["langsmith:nostream"],
    }
    
    # Step 2: Get report section and compressed research from state
    report_section = state.get("report_section", "")
    compressed_research = state.get("compressed_research", "")
    
    # Step 3: Configure the model
    write_model = configurable_model.with_config(write_report_section_model_config)
    
    # Step 4: Generate the report section using the prompt
    prompt_content = write_report_section_prompt.format(
        report_section=report_section,
        findings=compressed_research,
        date=get_today_str(),
    )
    
    response = await write_model.ainvoke([HumanMessage(content=prompt_content)])
    
    # Step 5: Return the written section
    sketch_content = str(response.content)
    return Command(
        goto=END,
        update={
            "report_section_sketch": sketch_content,
        },
    )

# ========================================
# Report Supervisor Subgraph Construction
# ========================================
report_supervisor_builder = StateGraph(
    ReportSupervisorState, config_schema=Configuration
)

report_supervisor_builder.add_node("report_supervisor", report_supervisor)
report_supervisor_builder.add_node("report_supervisor_tools", report_supervisor_tools)

report_supervisor_builder.add_edge(START, "report_supervisor")

# Compile the supervisor subgraph
report_supervisor_subgraph = report_supervisor_builder.compile()

# ========================================
# Report Researcher Subgraph Construction
# ========================================
report_researcher_builder = StateGraph(
    ReportResearcherState, output=ResearcherOutputState, config_schema=Configuration
)

report_researcher_builder.add_node("report_researcher", report_researcher)
report_researcher_builder.add_node("report_researcher_tools", report_researcher_tools)
report_researcher_builder.add_node("compress_report_research", compress_report_research)
report_researcher_builder.add_node("write_report_section", write_report_section)

report_researcher_builder.add_edge(START, "report_researcher")
report_researcher_builder.add_edge("compress_report_research", "write_report_section")
report_researcher_builder.add_edge("write_report_section", END)

# Compile researcher subgraph (usado por el supervisor)
report_researcher_subgraph = report_researcher_builder.compile()
