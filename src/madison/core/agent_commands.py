"""Agent management commands for Madison CLI."""

import logging
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from madison.core.agent_registry import AgentManager, AgentDefinition, AGENT_TEMPLATES
from madison.utils.input_handler import MadisonPrompt

logger = logging.getLogger(__name__)
console = Console()


async def handle_agent_command(args: str, agent_manager: AgentManager, prompt: MadisonPrompt) -> Optional[AgentDefinition]:
    """Handle /agent commands.

    Args:
        args: Command arguments
        agent_manager: Agent manager instance
        prompt: Input prompt handler

    Returns:
        Selected agent if /agent use command, None otherwise
    """
    parts = args.split(maxsplit=1) if args else []
    subcommand = parts[0].lower() if parts else ""
    rest_args = parts[1] if len(parts) > 1 else ""

    if not subcommand or subcommand == "list":
        # /agent or /agent list [category]
        category = rest_args if rest_args else None
        list_agents(agent_manager, category)
        return None

    elif subcommand == "templates":
        # /agent templates
        show_templates()
        return None

    elif subcommand == "create":
        # /agent create
        agent = await create_agent_wizard(agent_manager, prompt)
        return None

    elif subcommand == "use":
        # /agent use <category> <name>
        if not rest_args:
            console.print("[red]Usage: /agent use <category> <name>[/red]")
            return None

        parts = rest_args.split(maxsplit=1)
        if len(parts) < 2:
            console.print("[red]Usage: /agent use <category> <name>[/red]")
            return None

        category, name = parts
        agent = agent_manager.get_agent(category, name)
        if agent:
            console.print(f"[green]✓ Switched to agent:[/green] {agent.name}")
            return agent
        else:
            console.print(f"[red]Agent not found:[/red] {category}/{name}")
            return None

    elif subcommand == "view":
        # /agent view <category> <name>
        if not rest_args:
            console.print("[red]Usage: /agent view <category> <name>[/red]")
            return None

        parts = rest_args.split(maxsplit=1)
        if len(parts) < 2:
            console.print("[red]Usage: /agent view <category> <name>[/red]")
            return None

        category, name = parts
        agent = agent_manager.get_agent(category, name)
        if agent:
            view_agent(agent)
        else:
            console.print(f"[red]Agent not found:[/red] {category}/{name}")
        return None

    elif subcommand == "delete":
        # /agent delete <category> <name>
        if not rest_args:
            console.print("[red]Usage: /agent delete <category> <name>[/red]")
            return None

        parts = rest_args.split(maxsplit=1)
        if len(parts) < 2:
            console.print("[red]Usage: /agent delete <category> <name>[/red]")
            return None

        category, name = parts
        # Ask for confirmation
        response = console.input(f"Delete agent: {category}/{name}? [y/N]: ").lower()
        if response in ("y", "yes"):
            if agent_manager.delete_agent(category, name, "user"):
                console.print(f"[green]✓ Deleted agent:[/green] {category}/{name}")
            else:
                console.print(f"[red]Agent not found:[/red] {category}/{name}")
        else:
            console.print("[yellow]Deletion cancelled.[/yellow]")
        return None

    else:
        console.print(f"[red]Unknown agent subcommand: {subcommand}[/red]")
        console.print("[dim]Available subcommands: list, templates, create, use, view, delete[/dim]")
        return None


def list_agents(agent_manager: AgentManager, category: Optional[str] = None) -> None:
    """List all agents, optionally filtered by category."""
    agents = agent_manager.list_agents(category=category)

    if not agents:
        console.print("[yellow]No agents found.[/yellow]")
        return

    console.print("\n[bold]Available Agents:[/bold]")

    # Group by category
    by_category = {}
    for agent in agents:
        if agent.category not in by_category:
            by_category[agent.category] = []
        by_category[agent.category].append(agent)

    for cat in sorted(by_category.keys()):
        console.print(f"\n  [cyan]{cat.upper()}[/cyan]")
        for agent in sorted(by_category[cat], key=lambda a: a.name):
            scope_indicator = "[yellow]project[/yellow]" if agent.scope == "project" else "[dim]user[/dim]"
            console.print(f"    • {agent.name} {scope_indicator}")
            console.print(f"      {agent.description}")


def show_templates() -> None:
    """Show available agent templates."""
    console.print("\n[bold]Available Agent Templates:[/bold]")

    # Group templates by category
    by_category = {}
    for template_key, template in AGENT_TEMPLATES.items():
        if template.category not in by_category:
            by_category[template.category] = []
        by_category[template.category].append(template)

    for cat in sorted(by_category.keys()):
        console.print(f"\n  [cyan]{cat.upper()}[/cyan]")
        for template in sorted(by_category[cat], key=lambda a: a.name):
            console.print(f"    • {template.name}")
            console.print(f"      {template.description}")

    console.print("\n[dim]Use '/agent create' to create a new agent from a template[/dim]")


async def create_agent_wizard(agent_manager: AgentManager, prompt: MadisonPrompt) -> Optional[AgentDefinition]:
    """Interactive wizard to create a new agent."""
    console.print("\n[bold cyan]Madison Agent Creator[/bold cyan]")
    console.print("=" * 50)

    # Ask if they want to start from a template
    console.print("\n[bold]Starting Point:[/bold]")
    console.print("  1. Blank agent")
    console.print("  2. Agent from template")
    choice = console.input("Choose (1 or 2): ").strip()

    agent = None
    if choice == "2":
        # Show templates and let them choose
        console.print("\n[bold]Available Templates:[/bold]")
        templates_list = list(AGENT_TEMPLATES.values())
        for i, template in enumerate(templates_list, 1):
            console.print(f"  {i}. {template.name} - {template.description}")

        try:
            template_choice = int(console.input("\nSelect template (number): "))
            if 1 <= template_choice <= len(templates_list):
                agent = templates_list[template_choice - 1]
                console.print(f"\n[green]Starting from template:[/green] {agent.name}")
            else:
                console.print("[yellow]Invalid choice, starting blank[/yellow]")
        except ValueError:
            console.print("[yellow]Invalid input, starting blank[/yellow]")

    # Get agent details
    console.print("\n[bold]Agent Details:[/bold]")

    if not agent:
        # Get basic info
        name = console.input("Agent Name: ").strip()
        category = console.input("Category (analysis/writing/development/custom): ").strip()
        description = console.input("Description: ").strip()
        prompt_text = ""
    else:
        # Pre-fill from template
        name = console.input(f"Agent Name [{agent.name}]: ").strip() or agent.name
        category = console.input(f"Category [{agent.category}]: ").strip() or agent.category
        description = console.input(f"Description [{agent.description}]: ").strip() or agent.description
        prompt_text = agent.prompt

    # Get optional settings
    console.print("\n[bold]Optional Settings:[/bold]")
    model = console.input("Model (leave blank for default): ").strip() or None
    temperature = None
    max_tokens = None

    try:
        temp_input = console.input("Temperature (0.0-2.0, leave blank for default): ").strip()
        if temp_input:
            temperature = float(temp_input)
    except ValueError:
        console.print("[yellow]Invalid temperature, skipping[/yellow]")

    try:
        tokens_input = console.input("Max tokens (leave blank for default): ").strip()
        if tokens_input:
            max_tokens = int(tokens_input)
    except ValueError:
        console.print("[yellow]Invalid max_tokens, skipping[/yellow]")

    # Get tools list
    tools_input = console.input(
        "Tools (comma-separated: execute_command,read_file,write_file,search_web, leave blank for all): "
    ).strip()
    tools = None
    if tools_input:
        tools = [t.strip() for t in tools_input.split(",")]

    # Ask for scope
    console.print("\n[bold]Storage Scope:[/bold]")
    console.print("  1. User (stored in ~/.madison/agents/)")
    console.print("  2. Project (stored in ./.madison/agents/)")
    scope_choice = console.input("Choose (1 or 2) [1]: ").strip() or "1"
    scope = "project" if scope_choice == "2" else "user"

    # Get/edit prompt
    if not prompt_text:
        console.print("\n[bold]Agent Prompt:[/bold]")
        console.print("[dim]Enter the system prompt for this agent (type 'END' on a new line to finish):[/dim]")
        lines = []
        while True:
            line = console.input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        prompt_text = "\n".join(lines)
    else:
        console.print(f"\n[bold]Agent Prompt (from template):[/bold]")
        console.print(prompt_text[:200] + "...")
        edit = console.input("Edit prompt? [y/N]: ").lower()
        if edit in ("y", "yes"):
            console.print("[dim]Enter new prompt (type 'END' on a new line to finish):[/dim]")
            lines = []
            while True:
                line = console.input()
                if line.strip().upper() == "END":
                    break
                lines.append(line)
            prompt_text = "\n".join(lines)

    # Create the agent
    agent = AgentDefinition(
        name=name,
        category=category,
        description=description,
        prompt=prompt_text,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        scope=scope,
    )

    try:
        agent_manager.create_agent(agent)
        console.print(f"\n[green]✓ Agent created successfully![/green]")
        console.print(f"[dim]Location:[/dim] {agent.file_path}")
        console.print(f"\n[dim]Use it with: /agent use {agent.category} {agent.name}[/dim]")
        return agent
    except Exception as e:
        console.print(f"\n[red]Error creating agent:[/red] {e}")
        return None


def view_agent(agent: AgentDefinition) -> None:
    """Display agent details."""
    console.print(f"\n[bold cyan]{agent.name}[/bold cyan]")
    console.print("=" * 50)

    console.print(f"\n[bold]Category:[/bold] {agent.category}")
    console.print(f"[bold]Description:[/bold] {agent.description}")
    console.print(f"[bold]Version:[/bold] {agent.version}")
    console.print(f"[bold]Scope:[/bold] {agent.scope}")

    if agent.model:
        console.print(f"[bold]Model:[/bold] {agent.model}")
    if agent.temperature is not None:
        console.print(f"[bold]Temperature:[/bold] {agent.temperature}")
    if agent.max_tokens:
        console.print(f"[bold]Max Tokens:[/bold] {agent.max_tokens}")
    if agent.tools:
        console.print(f"[bold]Tools:[/bold] {', '.join(agent.tools)}")

    console.print(f"\n[bold]Prompt:[/bold]")
    console.print(Panel(agent.prompt, title="Agent Prompt", expand=False))
