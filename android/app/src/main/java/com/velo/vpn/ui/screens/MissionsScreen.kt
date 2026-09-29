package com.velo.vpn.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.data.MissionItemDto
import com.velo.vpn.ui.AccountViewModel
import com.velo.vpn.ui.RewardsViewModel
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.components.PrimaryButton
import com.velo.vpn.ui.components.VeloCard
import com.velo.vpn.ui.components.VeloHeader
import com.velo.vpn.ui.theme.HeartPink
import com.velo.vpn.ui.theme.Muted
import com.velo.vpn.ui.theme.VeloPurple

@Composable
fun MissionsScreen(nav: NavHostController, vm: RewardsViewModel, accountVm: AccountViewModel) {
    val state by vm.state.collectAsState()
    val account by accountVm.state.collectAsState()
    val context = LocalContext.current
    var tab by remember { mutableStateOf("روزانه") }
    LaunchedEffect(Unit) { vm.refreshMissions() }
    LaunchedEffect(tab) {
        when (tab) {
            "هفتگی" -> vm.refreshWeekly()
            "یک‌باره" -> vm.refreshOneTime()
        }
    }

    Scaffold { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            VeloHeader(showBack = true, hearts = account.hearts, onBack = { nav.popBackStack() })
            Text("ماموریت‌ها", fontSize = 30.sp, fontWeight = FontWeight.ExtraBold)
            Text("ماموریت‌های ساده را انجام دهید و قلب جمع کنید.", color = Muted)

            SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                listOf("روزانه", "هفتگی", "یک‌باره").forEachIndexed { i, title ->
                    SegmentedButton(
                        selected = tab == title,
                        onClick = { tab = title },
                        shape = SegmentedButtonDefaults.itemShape(i, 3),
                        label = { Text(title) },
                    )
                }
            }

            if (tab == "هفتگی") {
                val week = state.weekly
                if (state.loadingWeekly) LinearProgressIndicator(Modifier.fillMaxWidth())
                if (week != null) {
                    val completedCount = week.missions.count { it.complete }
                    VeloCard(Modifier.fillMaxWidth()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text("پیشرفت این هفته", fontWeight = FontWeight.Bold)
                                Text("$completedCount از ${week.missions.size} ماموریت", color = Muted, fontSize = 12.sp)
                            }
                            Text("+${week.weeklyBonusHearts} ♥", color = HeartPink, fontWeight = FontWeight.Bold)
                        }
                        Spacer(Modifier.height(10.dp))
                        LinearProgressIndicator(
                            progress = { if (week.missions.isEmpty()) 0f else completedCount.toFloat() / week.missions.size },
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                    week.missions.forEach { item ->
                        MissionRow(item, week.accountRequiredForHearts) { vm.claimWeekly(item.key) }
                    }
                    if (week.weeklyComplete) {
                        VeloCard(Modifier.fillMaxWidth()) {
                            Text("جایزه تکمیل هفته", fontWeight = FontWeight.Bold)
                            Text("همه ماموریت‌های این هفته کامل شده‌اند.", color = Muted, fontSize = 12.sp)
                            Spacer(Modifier.height(10.dp))
                            when {
                                week.weeklyBonusClaimed -> Text("پاداش دریافت شد ✓", color = VeloPurple, fontWeight = FontWeight.Bold)
                                week.accountRequiredForHearts -> PrimaryButton("برای دریافت قلب وارد حساب شوید") { nav.navigate(Routes.Account) }
                                else -> PrimaryButton("دریافت +${week.weeklyBonusHearts} قلب") { vm.claimWeekly("weekly_bonus") }
                            }
                        }
                    }
                }
            } else if (tab == "یک‌باره") {
                if (state.loadingOneTime) LinearProgressIndicator(Modifier.fillMaxWidth())
                val once = state.oneTime
                if (once?.accountRequiredForHearts == true) {
                    VeloCard(Modifier.fillMaxWidth()) {
                        Text("برای دریافت پاداش یک‌باره، ابتدا با ایمیل وارد حساب Velo شوید.", fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(10.dp))
                        PrimaryButton("ورود با ایمیل") { nav.navigate(Routes.Account) }
                    }
                }
                once?.missions?.forEach { mission ->
                    VeloCard(Modifier.fillMaxWidth()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(mission.title, fontWeight = FontWeight.Bold)
                                Text(
                                    when {
                                        mission.claimed -> "پاداش دریافت شده"
                                        !mission.enabled -> "به‌زودی"
                                        mission.opened -> "صفحه باز شده؛ پاداش آماده دریافت است"
                                        else -> "یک‌بار قابل انجام"
                                    },
                                    color = Muted,
                                    fontSize = 11.sp,
                                )
                            }
                            Text("+${mission.hearts} ♥", color = HeartPink, fontWeight = FontWeight.Bold)
                        }
                        if (mission.enabled && !once.accountRequiredForHearts && !mission.claimed) {
                            Spacer(Modifier.height(8.dp))
                            if (!mission.opened) {
                                OutlinedButton(onClick = {
                                    vm.openOneTime(mission.key) { url ->
                                        runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
                                    }
                                }) { Text("باز کردن") }
                            } else {
                                OutlinedButton(onClick = { vm.claimOneTime(mission.key) }) { Text("دریافت پاداش") }
                            }
                        }
                    }
                }
            } else {
                val today = state.missions
                if (state.loadingMissions) LinearProgressIndicator(Modifier.fillMaxWidth())
                if (today != null) {
                    val completedCount = today.missions.count { it.complete }
                    VeloCard(Modifier.fillMaxWidth()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text("پیشرفت امروز", fontWeight = FontWeight.Bold)
                                Text("$completedCount از ${today.missions.size} ماموریت", color = Muted, fontSize = 12.sp)
                            }
                            Text("+${today.dailyBonusHearts} ♥", color = HeartPink, fontWeight = FontWeight.Bold)
                        }
                        Spacer(Modifier.height(10.dp))
                        LinearProgressIndicator(
                            progress = { if (today.missions.isEmpty()) 0f else completedCount.toFloat() / today.missions.size },
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }

                    today.missions.forEach { MissionRow(it, today.accountRequiredForHearts) { vm.claimMission(it.key) } }

                    if (today.dailyComplete) {
                        VeloCard(Modifier.fillMaxWidth()) {
                            Text("جایزه تکمیل روز", fontWeight = FontWeight.Bold)
                            Text("همه ماموریت‌های امروز کامل شده‌اند.", color = Muted, fontSize = 12.sp)
                            Spacer(Modifier.height(10.dp))
                            if (today.dailyBonusClaimed) {
                                Text("پاداش دریافت شد ✓", color = VeloPurple, fontWeight = FontWeight.Bold)
                            } else if (today.accountRequiredForHearts) {
                                PrimaryButton("برای دریافت قلب وارد حساب شوید") { nav.navigate(Routes.Account) }
                            } else {
                                PrimaryButton("دریافت +${today.dailyBonusHearts} قلب") { vm.claimMission("daily_bonus") }
                            }
                        }
                    }
                }
            }

            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            state.info?.let { Text(it, color = VeloPurple) }
        }
    }
}

@Composable
private fun MissionRow(item: MissionItemDto, accountRequired: Boolean, onClaim: () -> Unit) {
    VeloCard(Modifier.fillMaxWidth()) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(item.title, fontWeight = FontWeight.Bold)
                Text("${item.progress} / ${item.target}", color = Muted, fontSize = 11.sp)
            }
            Icon(Icons.Default.Favorite, null, tint = HeartPink, modifier = Modifier.size(16.dp))
            Text(" +${item.hearts}", color = HeartPink, fontWeight = FontWeight.Bold)
            Spacer(Modifier.width(8.dp))
            when {
                item.claimed -> Icon(Icons.Default.CheckCircle, null, tint = VeloPurple)
                item.complete && !accountRequired -> TextButton(onClick = onClaim) { Text("دریافت") }
            }
        }
        Spacer(Modifier.height(8.dp))
        LinearProgressIndicator(
            progress = { (item.progress.toFloat() / item.target.coerceAtLeast(1)).coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxWidth(),
        )
    }
}
