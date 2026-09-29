package com.velo.vpn.ui.screens

import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.BuildConfig
import com.velo.vpn.diagnostics.CrashStore
import com.velo.vpn.ui.AccountViewModel
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.components.*
import com.velo.vpn.ui.theme.Muted

@Composable fun SettingsScreen(nav: NavHostController, accountViewModel: AccountViewModel) {
    val account by accountViewModel.state.collectAsState()
    val uriHandler = LocalUriHandler.current
    val context = LocalContext.current
    val crash = remember { CrashStore(context).lastCrash() }
    Scaffold(bottomBar = { VeloBottomBar(nav, Routes.Settings) }) { pad ->
        Column(Modifier.fillMaxSize().padding(pad).padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            VeloHeader(hearts = account.hearts)
            Text("تنظیمات", fontSize=30.sp, fontWeight=FontWeight.ExtraBold)
            VeloCard(Modifier.fillMaxWidth(), onClick={nav.navigate(Routes.Premium)}) { Row { Icon(Icons.Default.WorkspacePremium,null,tint=com.velo.vpn.ui.theme.VeloPurple); Spacer(Modifier.width(12.dp)); Column {Text("اشتراک Premium",fontWeight=FontWeight.Bold);Text(if(account.subscriptionActive) "اشتراک فعال" else "ارتقا بدون تبلیغ و محدودیت",color=Muted,fontSize=12.sp)} } }
            FeatureRow(Icons.Default.Person, "حساب کاربری", if(account.loggedIn) account.email else "ورود با ایمیل") { nav.navigate(Routes.Account) }
            FeatureRow(Icons.Default.Dns, "انتخاب سرور", null) { nav.navigate(Routes.Servers) }
            FeatureRow(Icons.Default.DarkMode, "ظاهر برنامه", "روشن / تیره") {}
            FeatureRow(Icons.Default.Language, "زبان", "فارسی") {}
            FeatureRow(Icons.Default.Notifications, "اعلان‌ها", null) {}
            FeatureRow(Icons.Default.Shield, "حریم خصوصی", null) { uriHandler.openUri(BuildConfig.PRIVACY_URL) }
            FeatureRow(Icons.Default.Info, "شرایط و درباره Velo", "نسخه ${BuildConfig.VERSION_NAME}") { uriHandler.openUri(BuildConfig.TERMS_URL) }
            FeatureRow(Icons.Default.SupportAgent, "تماس با پشتیبانی", crash?.let { "کد خطای قبلی: ${it.incidentId}" }) {
                val subject = Uri.encode("پشتیبانی Velo ${BuildConfig.VERSION_NAME}")
                val bodyText = crash?.let { "\n\nکد خطای محلی: ${it.incidentId}" }.orEmpty()
                val body = Uri.encode(bodyText)
                uriHandler.openUri("mailto:${BuildConfig.SUPPORT_EMAIL}?subject=$subject&body=$body")
            }
        }
    }
}
