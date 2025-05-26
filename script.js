// static/js/script.js
document.addEventListener('DOMContentLoaded', () => {
    const researchAreaInput = document.getElementById('researchAreaInput');
    const startResearchBtn = document.getElementById('startResearchBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorMessageDiv = document.getElementById('errorMessage');
    
    const reportSectionDiv = document.getElementById('reportSection');
    const reportAreaTitleH2 = document.getElementById('reportAreaTitle');
    const reportContentDiv = document.getElementById('reportContent');

    const followUpQuestionInput = document.getElementById('followUpQuestion');
    const askFollowUpBtn = document.getElementById('askFollowUpBtn');
    const followUpLoadingIndicator = document.getElementById('followUpLoadingIndicator');
    const followUpErrorMessageDiv = document.getElementById('followUpErrorMessage');
    const followUpAnswerDiv = document.getElementById('followUpAnswer');

    let currentReportData = null; 
    let chartInstances = []; 

    marked.setOptions({
        breaks: true, 
        gfm: true,    
        sanitize: false
    });

    // --- Color Palette for Charts ---
    const baseColors = [
        { r: 26, g: 188, b: 156, a: 0.65 }, { r: 52, g: 152, b: 219, a: 0.65 }, // Teal, Blue
        { r: 155, g: 89, b: 182, a: 0.65 }, { r: 241, g: 196, b: 15, a: 0.75 }, // Purple, Yellow
        { r: 230, g: 126, b: 34, a: 0.65 }, { r: 231, g: 76, b: 60, a: 0.65 },  // Orange, Red
        { r: 46, g: 204, b: 113, a: 0.65 }, { r: 243, g: 156, b: 18, a: 0.75 }, // Green, Darker Orange
        { r: 52, g: 73, b: 94, a: 0.65 },   { r: 149, g: 165, b: 166, a: 0.65 },// Dark Blue-Gray, Mid Gray
        { r: 22, g: 160, b: 133, a: 0.65 }, { r: 41, g: 128, b: 185, a: 0.65 }, // Darker Teal, Darker Blue
        { r: 125, g: 60, b: 152, a: 0.65 }, { r: 211, g: 84, b: 0, a: 0.65 },   // Darker Purple, Burnt Orange
        { r: 189, g: 195, b: 199, a: 0.65 } // Light Gray (Concrete)
    ];

    function getRandomColor(isBorder = false, index = 0) {
        const colorObj = baseColors[index % baseColors.length];
        const alpha = isBorder ? '1' : (colorObj.a || '0.65').toString();
        return `rgba(${colorObj.r},${colorObj.g},${colorObj.b},${alpha})`;
    }

    function displayError(message, element = errorMessageDiv) {
        element.textContent = message;
        element.style.display = 'block';
    }

    function clearError(element = errorMessageDiv) {
        element.textContent = '';
        element.style.display = 'none';
    }
    
    function renderMarkdownToHtml(markdownText) {
        if (markdownText && typeof markdownText === 'string') {
            return marked.parse(markdownText);
        }
        return '<p><em>Content not available or in an unexpected format.</em></p>';
    }


    startResearchBtn.addEventListener('click', async () => {
        const area = researchAreaInput.value.trim();
        if (!area) {
            displayError('Please enter a geographical area.');
            return;
        }

        clearError();
        reportSectionDiv.style.display = 'none';
        reportContentDiv.innerHTML = '';
        chartInstances.forEach(chart => chart.destroy()); 
        chartInstances = [];
        followUpAnswerDiv.innerHTML = '';
        followUpQuestionInput.value = '';
        currentReportData = null;

        loadingIndicator.style.display = 'block';
        startResearchBtn.disabled = true;
        researchAreaInput.disabled = true;

        try {
            const response = await fetch('/research', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ area: area }) 
            });

            if (!response.ok) {
                let errorMsg = `HTTP error! Status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.detail || errorMsg;
                } catch (e) {
                    errorMsg = `${errorMsg} - ${response.statusText || 'Server error'}`;
                }
                throw new Error(errorMsg);
            }

            currentReportData = await response.json();
            displayReport(currentReportData);

        } catch (error) {
            console.error('Research error:', error);
            displayError(`Failed to generate health report: ${error.message}`);
            if (currentReportData && currentReportData.full_report_markdown && currentReportData.full_report_markdown.startsWith("Error:")) {
                 reportContentDiv.innerHTML = `<div class="report-subsection"><h3>Raw AI Error Details</h3><pre style="white-space: pre-wrap; word-wrap: break-word;">${currentReportData.full_report_markdown}</pre></div>`;
                 reportSectionDiv.style.display = 'block';
            }
        } finally {
            loadingIndicator.style.display = 'none';
            startResearchBtn.disabled = false;
            researchAreaInput.disabled = false;
        }
    });

    function displayReport(data) {
        if (!data || !data.area_name || typeof data.full_report_markdown !== 'string') {
            displayError("Received invalid report data from the server.");
            reportSectionDiv.style.display = 'none';
            return;
        }
        reportAreaTitleH2.textContent = `Comprehensive Health Analysis Report for: ${data.area_name}`;
        
        chartInstances.forEach(chart => chart.destroy());
        chartInstances = [];
        reportContentDiv.innerHTML = '';

        if (data.full_report_markdown.startsWith("Error:")) {
            reportContentDiv.innerHTML = `<div class="report-subsection"><h3>Report Generation Error</h3><pre style="white-space: pre-wrap; word-wrap: break-word;">${data.full_report_markdown}</pre></div>`;
            reportSectionDiv.style.display = 'block';
            return;
        }
        
        let markdownWithPlaceholders = data.full_report_markdown;
        const chartDataForRendering = []; 
        const chartDirectiveRegex = /CHART_DATA:\s*TYPE=(?<type>\w+)\s*TITLE="(?<title>[^"]+)"\s*LABELS=(?<labels>\[[^\]]*\])\s*DATA=(?<data>\[[^\]]*\])(?:\s*SOURCE="(?<source>[^"]+)")?/g;
        
        let match;
        let chartIndex = 0;
        while ((match = chartDirectiveRegex.exec(data.full_report_markdown)) !== null) {
            const placeholderId = `chart-placeholder-${chartIndex}`;
            markdownWithPlaceholders = markdownWithPlaceholders.replace(match[0], `<div id="${placeholderId}" class="chart-render-target"></div>`);
            const parsedChart = data.charts[chartIndex]; 
            if (parsedChart) {
                 chartDataForRendering.push({ placeholderId, chartConfig: parsedChart });
            } else {
                console.warn(`Could not find parsed chart data for directive: ${match[0]}`);
            }
            chartIndex++;
        }

        reportContentDiv.innerHTML = renderMarkdownToHtml(markdownWithPlaceholders);

        if (chartDataForRendering.length > 0) {
            chartDataForRendering.forEach((item, currentChartOverallIndex) => { // Use overall index for color variation
                const placeholderElement = document.getElementById(item.placeholderId);
                if (placeholderElement) {
                    const canvas = document.createElement('canvas');
                    canvas.id = `chart-canvas-${item.placeholderId.split('-').pop()}`; 
                    placeholderElement.appendChild(canvas);
                    
                    const ctx = canvas.getContext('2d');
                    try {
                        const chartConfig = item.chartConfig;
                        const newChart = new Chart(ctx, {
                            type: chartConfig.type.toLowerCase() || 'bar', // Ensure lowercase
                            data: {
                                labels: chartConfig.labels,
                                datasets: chartConfig.datasets.map((ds, datasetIndex) => {
                                    let bgColors;
                                    let borderColors;
                                    const chartTypeLower = chartConfig.type.toLowerCase();

                                    if (['pie', 'doughnut', 'bar'].includes(chartTypeLower)) {
                                        bgColors = ds.data.map((_, dataPointIndex) => 
                                            getRandomColor(false, currentChartOverallIndex * 10 + datasetIndex * 5 + dataPointIndex)
                                        );
                                        // For bar charts, border often same as bg but solid, or a distinct darker shade
                                        // For pie/doughnut, border often a bit darker or white for separation
                                        if (chartTypeLower === 'bar') {
                                            borderColors = bgColors.map(color => color.replace(/rgba\(([^,]+),([^,]+),([^,]+),[^)]+\)/, 'rgb($1,$2,$3)')); // Solid version
                                        } else { // pie, doughnut
                                            borderColors = '#fff'; // White borders for separation often look good
                                        }
                                    } else { // line, radar, etc.
                                        const colorBaseIndex = currentChartOverallIndex * 10 + datasetIndex;
                                        bgColors = ds.backgroundColor || getRandomColor(false, colorBaseIndex);
                                        borderColors = ds.borderColor || getRandomColor(true, colorBaseIndex);
                                    }

                                    return {
                                        label: ds.label || chartConfig.title || `Dataset ${datasetIndex + 1}`,
                                        data: ds.data,
                                        backgroundColor: bgColors, 
                                        borderColor: borderColors,
                                        borderWidth: (chartTypeLower === 'pie' || chartTypeLower === 'doughnut') ? 2 : 1.5, // Thicker border for pie/doughnut separation
                                        tension: (chartTypeLower === 'line' || chartTypeLower === 'radar') ? 0.3 : 0,
                                        fill: (chartTypeLower === 'radar' && chartConfig.datasets.length === 1) ? 'origin' : 
                                              (chartTypeLower === 'line' && chartConfig.datasets.length === 1 && ds.data.length > 1) ? 'origin' : false,
                                    };
                                })
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: true,
                                animation: { duration: 600, easing: 'easeOutQuart' },
                                plugins: {
                                    title: {
                                        display: !!chartConfig.title,
                                        text: chartConfig.title,
                                        font: { size: 16, weight: 'bold' },
                                        padding: { top: 10, bottom: (chartConfig.source ? 5 : 20) }
                                    },
                                    subtitle: {
                                        display: !!chartConfig.source,
                                        text: chartConfig.source ? `Source: ${chartConfig.source}` : '',
                                        font: { size: 10, style: 'italic' },
                                        color: '#666',
                                        padding: { bottom: 15 }
                                    },
                                    legend: {
                                        display: chartConfig.datasets.length > 1 || ['pie', 'doughnut'].includes(chartConfig.type.toLowerCase()),
                                        position: 'top',
                                        labels: { font: { size: 12 } }
                                    },
                                    tooltip: {
                                        enabled: true, 
                                        mode: 'index', // 'index' for line/bar, 'nearest' might be better for pie/doughnut if single dataset
                                        intersect: false, // Usually better for discoverability
                                        callbacks: {
                                            label: function(context) {
                                                let label = '';
                                                const chartTypeLower = context.chart.config.type; // Get type from context
                                                
                                                if (chartTypeLower === 'pie' || chartTypeLower === 'doughnut') {
                                                    label = context.label || ''; // Label of the slice
                                                } else {
                                                    label = context.dataset.label || ''; // Dataset label for other types
                                                }

                                                if (label) { label += ': '; }

                                                let value;
                                                if (context.parsed.y !== undefined) value = context.parsed.y;
                                                else if (context.parsed.r !== undefined) value = context.parsed.r; // radar
                                                else value = context.parsed; // pie, doughnut

                                                if (value !== null && value !== undefined) {
                                                    label += new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
                                                }
                                                return label;
                                            }
                                        }
                                    }
                                },
                                scales: ['bar', 'line', 'scatter'].includes(chartConfig.type.toLowerCase()) ? {
                                    y: { 
                                        beginAtZero: true,
                                        ticks: { font: { size: 11 }, callback: value => Number(value.toFixed(1)) },
                                        grid: { color: 'rgba(200, 200, 200, 0.2)' }
                                    },
                                    x: {
                                        ticks: { font: { size: 11 }, autoSkip: true, maxTicksLimit: 10 },
                                        grid: { display: false }
                                    }
                                } : chartConfig.type.toLowerCase() === 'radar' ? {
                                    r: {
                                        angleLines: { display: true, color: 'rgba(200, 200, 200, 0.2)' },
                                        suggestedMin: 0,
                                        pointLabels: { font: { size: 11 } },
                                        grid: { color: 'rgba(200, 200, 200, 0.2)' },
                                        ticks: { backdropColor: 'transparent', font: {size: 10}, callback: value => Number(value.toFixed(1)) }
                                    }
                                } : {} // No scales for pie/doughnut generally needed in options
                            }
                        });
                        chartInstances.push(newChart);
                    } catch(e) {
                        console.error("Error rendering chart:", e, "Chart Data:", JSON.stringify(chartConfig, null, 2));
                        placeholderElement.innerHTML = `<p class="error-message">Could not render chart: ${chartConfig.title || 'Untitled Chart'}. Error: ${e.message}</p>`;
                    }
                } else {
                    console.warn(`Placeholder element ${item.placeholderId} not found in DOM after Markdown rendering.`);
                }
            });
        }
        
        reportSectionDiv.style.display = 'block';
    }
    
    askFollowUpBtn.addEventListener('click', async () => {
        const question = followUpQuestionInput.value.trim();
        if (!question) {
            displayError('Please enter a follow-up question.', followUpErrorMessageDiv);
            return;
        }
        if (!currentReportData || !currentReportData.report_id || !currentReportData.full_text_for_follow_up) {
            displayError('No report context available for follow-up. Please generate a report first.', followUpErrorMessageDiv);
            return;
        }

        clearError(followUpErrorMessageDiv);
        followUpAnswerDiv.innerHTML = '';
        followUpLoadingIndicator.style.display = 'block';
        askFollowUpBtn.disabled = true;
        followUpQuestionInput.disabled = true;

        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    report_id: currentReportData.report_id,
                    question: question,
                    report_context: currentReportData.full_text_for_follow_up 
                })
            });

            if (!response.ok) {
                let errorMsg = `HTTP error! Status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.detail || errorMsg;
                } catch (e) {
                     errorMsg = `${errorMsg} - ${response.statusText || 'Server error'}`;
                }
                throw new Error(errorMsg);
            }

            const answerData = await response.json();
            followUpAnswerDiv.innerHTML = renderMarkdownToHtml(answerData.answer);

        } catch (error) {
            console.error('Follow-up error:', error);
            displayError(`Failed to get answer: ${error.message}`, followUpErrorMessageDiv);
        } finally {
            followUpLoadingIndicator.style.display = 'none';
            askFollowUpBtn.disabled = false;
            followUpQuestionInput.disabled = false;
        }
    });
});